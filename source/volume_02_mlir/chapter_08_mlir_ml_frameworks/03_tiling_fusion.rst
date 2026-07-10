.. _mlir-11-07-03:

========================================
Tiling、Fusion 与 Bufferization
========================================

Tiling、Fusion 和 Bufferization 是 MLIR 中**张量计算优化的三大支柱** 。
它们解决了如何将大张量计算高效映射到硬件的核心问题。

.. rst-class:: center

   这三个技术是 MLIR 的"性能引擎"——它们决定了最终代码有多快。

.. admonition:: 类比数据库：Tiling 是分区，Fusion 是 JOIN 下推
   :class: note

   把张量计算想象成数据库查询：

   - **Tiling** ≈ 表分区——把大矩阵切成小块，每块 fit 进 L1/共享内存
   - **Fusion** ≪ JOIN 下推——把 ``matmul + bias + relu`` 合并为一次遍历，
     避免写回中间结果到内存
   - **Bufferization** ≈ 查询计划中的内存分配——决定哪些中间结果可以原地复用

   Google 的 XLA 早在 HLO 层就做 Fusion；MLIR 的优势是把这件事
   推迟到 linalg 层，利用 ``indexing_maps`` 做更通用的融合判定。
   一条经验法则：**在最高层做最多的 Fusion，再逐层降级** 。

Tiling（分片）
====================

Tiling 将大张量计算**分割为小块** （tiles），使得每小块可以放入
CPU 的 L1 缓存或 GPU 的共享内存中。

**分片前（整体计算）**

.. code-block:: text

   // 整个矩阵乘法一次完成
   %C = linalg.matmul ins(%A, %B : tensor<128x128xf32>, tensor<128x128xf32>)
       outs(%C_init : tensor<128x128xf32>) -> tensor<128x128xf32>

**分片后（4x4 block）**

.. code-block:: text

   // 外层循环控制 tile
   scf.for %ti = %c0 to %c128 step %c32 {
       scf.for %tj = %c0 to %c128 step %c32 {
           scf.for %tk = %c0 to %c128 step %c32 {
               // 只计算 32x32 的 tile
               // 数据局部性更好
               linalg.matmul
                   ins(%A_tile, %B_tile : tensor<32x32xf32>, tensor<32x32xf32>)
                   outs(%C_tile : tensor<32x32xf32>)
                   -> tensor<32x32xf32>
           }
       }
   }

MLIR 中通过 ``--linalg-tile`` 实现：

.. code-block:: console

   $ mlir-opt --linalg-tile="tile-sizes=32,32" input.mlir

**分片大小选择** 取决于目标架构：

- CPU：通常 64~256，匹配缓存行大小
- GPU：通常 16~32，匹配 warp/wavefront 大小
- 加速器：取决于片上 SRAM 大小

Fusion（融合）
====================

Fusion 将多个连续的操作**合并为一个** ，减少中间结果的读写开销。

**融合前（两个独立操作）**

.. code-block:: text

   // 加法 → 激活函数 = 两次张量读写
   %sum = linalg.add %a, %b : tensor<4xf32>
   %result = linalg.relu %sum : tensor<4xf32>

**融合后（合并为一个循环）**

.. code-block:: text

   // 融合的 generic 操作 = 一次循环，同时完成加法和 ReLU
   %result = linalg.generic {
       indexing_maps = [affine_map<(i) -> (i)>, affine_map<(i) -> (i)>],
       iterator_types = ["parallel"]
   } ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
     outs(%out : tensor<4xf32>) {
   ^bb0(%x: f32, %y: f32, %z: f32):
       %sum = arith.addf %x, %y : f32
       %relu = arith.maximumf %sum, %c0 : f32
       linalg.yield %relu : f32
   }

MLIR 中通过 ``--linalg-fuse-elementwise-ops`` 实现：

.. code-block:: console

   $ mlir-opt --linalg-fuse-elementwise-ops input.mlir

**Fusion 的好处** ：

- 减少中间张量的内存分配
- 减少缓存未命中
- 减少内核启动开销（GPU）
- 给后端提供更大的优化窗口

One-Shot Bufferization
==============================

One-Shot Bufferization 是 MLIR 的一种**一次性缓冲化**策略。它不同于
传统的"先分配再复制"策略，而是通过分析所有 tensor 的用途链，
一次性做出最优的缓冲化决策。

**核心思路** ：

.. code-block:: text

   1. 构建 tensor 的 use-def 链
   2. 分析每个 tensor 是否可以就地更新（in-place）
   3. 为不能就地更新的 tensor 插入分配
   4. 一次性完成所有转换

.. code-block:: console

   $ mlir-opt --one-shot-bufferize input.mlir

**就地更新的判断** ：

.. code-block:: text

   // 就地更新可行：%a 只被使用一次
   %r = linalg.add ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
       outs(%out : tensor<4xf32>)

   // 就地更新不可行：%a 被两个操作共同使用
   %r1 = linalg.add ins(%a, %b : tensor<4xf32>, tensor<4xf32>) ...
   %r2 = linalg.relu ins(%a : tensor<4xf32>) ...

典型优化 Pipeline
============================

.. code-block:: console

   $ mlir-opt \
       --linalg-tile="tile-sizes=32,32" \
       --linalg-fuse-elementwise-ops \
       --one-shot-bufferize \
       --linalg-lower-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       input.mlir

源码走读：Tiling 实现
================================

Tiling 的核心实现在
`Tiling.cpp <file:///workspace/llvm-project/mlir/lib/Dialect/Linalg/Transforms/Tiling.cpp>`__ 。
它将 ``linalg.generic`` 或 ``linalg.matmul`` 的外层循环拆分为 tile 循环 +
内部小矩阵计算，利用 ``indexing_maps`` 计算每个 tile 的索引偏移。

Fusion 则将相邻的 ``linalg`` 操作合并为单个 ``linalg.generic`` ，
减少中间 tensor 的分配。One-Shot Bufferization 的三阶段分析见
:ref:`mlir-11-06-02` 中对 `OneShotAnalysis.cpp <file:///workspace/llvm-project/mlir/lib/Dialect/Bufferization/Transforms/OneShotAnalysis.cpp>`__ 的解读。

三者的执行顺序通常是 **Tile → Fuse → Bufferize → LowerToLoops** ：
先优化张量计算的访问模式，再解决内存分配，最后展开为循环。

动手验证
==========

用项目 tensor 示例验证 bufferize + 循环展开管道：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/tensor_add.mlir \
       --one-shot-bufferize=bufferize-function-boundaries \
       --convert-linalg-to-loops

观察输出中 ``scf.for`` 循环内的 ``memref.load`` / ``memref.store`` 模式——
这正是 tiling 和 fusion 优化后最终展开的命令式形态。

本章小结
========

Tiling 优化数据局部性，Fusion 减少中间结果，Bufferization 解决内存分配——
三者共同构成 MLIR 张量计算的性能引擎。它们都在 linalg 层操作，
完成后接入标准的 scf → LLVM 降级管道。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
