.. _mlir-06-06-02:

=================
tensor → scf 降级
=================

从 ``tensor`` / ``linalg`` 到 ``scf`` / ``arith`` 的降级是 MLIR 计算
降级管道中的第一步。它将高层**张量计算**展开为显式的**标量循环**。

.. rst-class:: center

   tensor 是"值"，scf 是"控制流"。降级 tensor → scf 的本质是把
   隐式的张量计算转换为显式的循环计算。

.. admonition:: Bufferization：函数式张量的"落地"时刻
   :class: note

   ``tensor`` 是**不可变值语义**——``%1 = tensor.insert %v into %t[%i]``
   产生新 tensor，不修改旧值。这对分析和优化很友好，但硬件只有一块内存。

   **Bufferization** 就是把值语义的 tensor 映射到有地址的 memref：
   分析哪些 tensor 可以原地复用内存，哪些需要分配新 buffer。
   One-Shot Bufferization 用全局分析一次性完成，避免逐 Op 降级时
   反复 alloc/dealloc 的性能损失。

   这是 ML 编译器中最微妙的步骤之一——错误的 buffer 复用会导致
   静默的数据竞争，所以 MLIR 为此专门建了 ``Bufferization`` Dialect
   和详尽的冲突检测分析。

Bufferization：tensor → memref
=====================================

Bufferization 是 tensor 计算降级的第一步。它将不可变的 ``tensor`` 值
转换为可变的 ``memref`` （内存引用）。

**降级前（tensor 形式）**

.. code-block:: text

   func.func @add(%a: tensor<4xf32>, %b: tensor<4xf32>) ->
       tensor<4xf32> {
       %0 = linalg.add %a, %b : tensor<4xf32>
       func.return %0 : tensor<4xf32>
   }

**降级后（memref 形式）**

.. code-block:: text

   func.func @add(%a: memref<4xf32>, %b: memref<4xf32>,
                  %out: memref<4xf32>) {
       linalg.add ins(%a, %b : memref<4xf32>, memref<4xf32>)
           outs(%out : memref<4xf32>)
       func.return
   }

由 ``one-shot-bufferize`` Pass 完成：

.. code-block:: console

   $ mlir-opt --one-shot-bufferize input.mlir

One-Shot Bufferize 的核心策略是**就地缓冲** （in-place bufferization）。
它分析 tensor 的使用链，尽可能复用现有的缓冲区，避免内存分配。

**Bufferization 的主要挑战**：

- **别名分析**：判断两个 memref 是否指向同一内存区域
- **就地更新判断**：确认可以就地修改而不影响其他使用者
- **内存分配边界**：在无法就地更新时插入分配

linalg.generic 到 scf.for 的降级
====================================

**降级前（linalg.generic）**

.. code-block:: text

   %result = linalg.generic {
       indexing_maps = [
           affine_map<(i) -> (i)>,
           affine_map<(i) -> (i)>
       ],
       iterator_types = ["parallel"]
   } ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
     outs(%out : tensor<4xf32>) {
   ^bb0(%x: f32, %y: f32, %z: f32):
       %sum = arith.addf %x, %y : f32
       linalg.yield %sum : f32
   } -> tensor<4xf32>

**降级后（scf.for）**

.. code-block:: text

   %result = scf.for %i = %c0 to %c4 step %c1
       iter_args(%acc = %out) -> tensor<4xf32> {
       %a_elem = tensor.extract %a[%i] : tensor<4xf32>
       %b_elem = tensor.extract %b[%i] : tensor<4xf32>
       %sum = arith.addf %a_elem, %b_elem : f32
       %new = tensor.insert %sum into %acc[%i] : tensor<4xf32>
       scf.yield %new : tensor<4xf32>
   }

这个过程由 ``linalg-lower-to-loops`` Pass 完成。

矩阵乘法的展开
========================

矩阵乘法降级为三重嵌套循环：

.. code-block:: text

   %C = linalg.matmul ins(%A, %B : tensor<4x4xf32>, tensor<4x4xf32>)
       outs(%C_init : tensor<4x4xf32>) -> tensor<4x4xf32>

   // 降级后：
   scf.for %i = %c0 to %c4 step %c1 {
       scf.for %j = %c0 to %c4 step %c1 {
           scf.for %k = %c0 to %c4 step %c1 {
               %a = tensor.extract %A[%i, %k] : tensor<4x4xf32>
               %b = tensor.extract %B[%k, %j] : tensor<4x4xf32>
               %c = tensor.extract %C[%i, %j] : tensor<4x4xf32>
               %mul = arith.mulf %a, %b : f32
               %sum = arith.addf %c, %mul : f32
               %new = tensor.insert %sum into %C[%i, %j] : tensor<4x4xf32>
           }
       }
   }

降级管道示例
==================

.. code-block:: console

   $ mlir-opt \
       --linalg-generalize-named-ops \
       --linalg-lower-to-loops \
       --one-shot-bufferize \
       input.mlir

降级顺序很重要——先展开命名操作（如 ``linalg.matmul`` → ``linalg.generic`` ），
然后将通用操作降级为循环。

源码走读：Bufferization 的三阶段
======================================

``tensor`` 是不可变值语义，``memref`` 是可变内存引用。二者之间的转换由
One-Shot Bufferize Pass 完成，其实现分布在：

- `OneShotAnalysis.cpp <file:///workspace/llvm-project/mlir/lib/Dialect/Bufferization/Transforms/OneShotAnalysis.cpp>`__ —— 分析阶段
- `Bufferize.h <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Bufferization/Transforms/Bufferize.h>`__ —— 对外接口

``OneShotAnalysis.cpp`` 的文件头注释把流程拆为三个阶段，值得精读：

1. **分析**：判断哪些操作数可以就地缓冲（in-place），无需插入拷贝
2. **插入拷贝**：为不能就地缓冲的操作数在 tensor 世界插入 ``tensor.insert_slice`` 等
3. **Bufferize**：调用各操作的 ``BufferizableOpInterface::bufferize`` 完成转换

其中第 1 步是性能关键。注释明确指出分析依赖 ``BufferizableOpInterface``——
每个支持 bufferization 的 Op 都要声明自己的读写语义。如果分析失败，
bufferization 会拒绝生成"需要返回新分配缓冲区"的函数（除非显式允许）。

这就是为什么 ``one-shot-bufferize`` 不只是一个类型替换 Pass，而是带有
**别名分析** 和 **就地更新判断** 的完整算法。

源码走读：linalg → scf 循环展开
======================================

``linalg.generic`` 降级为 ``scf.for`` 的核心逻辑在
`Loops.cpp <file:///workspace/llvm-project/mlir/lib/Dialect/Linalg/Transforms/Loops.cpp>`__。

文件开头的 ``inlineRegionAndEmitStore`` 函数揭示了降级的本质：

.. code-block:: cpp

   // 克隆 linalg.generic 的 region 体，用当前循环索引处的元素替换 block 参数
   for (auto &op : block.without_terminator()) {
     auto *newOp = b.clone(op, map);
     map.map(op.getResults(), newOp->getResults());
   }

对每个循环索引，Pass 从输入 tensor/memref 中 ``load`` 元素，克隆 ``linalg.generic``
region 内的计算，再把结果 ``store`` 到输出。三重嵌套循环的矩阵乘法，
不过是这个模式在三个维度上各执行一次。

动手验证
==========

项目提供了可运行的降级示例，文件路径为 ``examples/mlir/chapter_06_lowering/tensor_add.mlir`` 。

.. code-block:: console

   # 第一步：bufferize（tensor → memref）
   mlir-opt examples/mlir/chapter_06_lowering/tensor_add.mlir \
       --one-shot-bufferize="bufferize-function-boundaries"

   # 第二步：展开为 scf.for 循环
   mlir-opt examples/mlir/chapter_06_lowering/tensor_add.mlir \
       --one-shot-bufferize="bufferize-function-boundaries" \
       --convert-linalg-to-loops

第二步的输出应包含 ``scf.for`` 循环体，内有 ``memref.load`` / ``memref.store``
和 ``arith.addf``——这正是前文"张量计算 → 标量循环"的文字描述在 IR 中的对应物。

.. note::

   ``--convert-linalg-to-loops`` 要求输入已经是 ``memref`` 形式。
   直接对 ``tensor`` 运行该 Pass 不会有效果——这印证了 bufferization
   是 tensor → scf 降级的必要前置步骤。

本章小结
========

tensor → scf 降级的本质是**语义展开**：把声明式的张量操作翻译为命令式的循环。
Bufferization 解决"tensor 不可变"与"循环需要读写内存"之间的矛盾；
linalg → loops 则利用 ``indexing_maps`` 和 ``iterator_types`` 自动生成正确的循环嵌套。

下一节 :ref:`mlir-06-06-03` 将继续把 scf/arith 降级到 LLVM Dialect。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
