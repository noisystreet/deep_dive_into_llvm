.. _mlir-10-10-03:

===================
Vector Dialect
===================

Vector Dialect 是 MLIR 中用于**显式向量化**的 Dialect。它提供了丰富的
向量操作，可以精确控制 SIMD 指令的生成。

.. rst-class:: center

   Vector Dialect 的设计目标：提供硬件无关的向量抽象，同时保留足够的
   SIMD 语义让后端生成高效的向量指令。

.. admonition:: Vector Dialect vs LLVM 自动向量化
   :class: note

   LLVM 的 Loop Vectorizer 从标量循环**自动推断** SIMD 机会——方便但
   不可控。Vector Dialect 走**显式向量**路线：前端或优化器直接生成
   ``vector.transfer_read``、``vector.fma`` 等 Op，精确控制向量宽度。

   两条路线互补：MLIR 在 linalg 层做 Tiling 后，可以选择
   降为 ``vector`` Dialect（显式 SIMD）或 ``scf`` 循环（交给 LLVM 自动向量化）。
   对已知向量宽度的硬件（如 AVX-512），显式 Vector Dialect 通常
   能生成更优代码——这也是 Buddy 编译器的核心策略。

向量类型
==================

Vector Dialect 定义了自己的向量类型：

.. code-block:: text

   vector<4xf32>          // 4 个 f32 的向量
   vector<8xi32>          // 8 个 i32 的向量
   vector<2x4xf32>        // 2x4 的 2D 向量（外层 2，内层 4）

向量的维度可以是**多维**的——但在降级时，多维向量会映射为对应维度
的 SIMD 指令序列。

核心操作
==================

**创建和转换**

.. code-block:: text

   // 创建常数向量
   %0 = vector.splat %val : vector<4xf32>

   // 类型转换
   %1 = vector.bitcast %0 : vector<4xf32> to vector<4xi32>

**读取和写入**

.. code-block:: text

   // 加载
   %vec = vector.load %ptr[%offset] : memref<1024xf32>, vector<4xf32>

   // 存储
   vector.store %vec, %ptr[%offset] : memref<1024xf32>, vector<4xf32>

   // 从向量中提取元素
   %elem = vector.extract %vec[2] : vector<4xf32>

   // 插入元素到向量
   %new_vec = vector.insert %elem, %vec[2] : vector<4xf32>

**Shuffle 和组合**

.. code-block:: text

   // 两个向量的交错组合
   %shuf = vector.shuffle %v1, %v2 [0, 1, 4, 5] : vector<4xf32>, vector<4xf32>

   // 转置
   %trans = vector.transpose %mat, [1, 0] : vector<2x4xf32>

**归约操作**

.. code-block:: text

   // 水平相加（将向量的所有元素相加）
   %sum = vector.reduction add, %vec : vector<4xf32> -> f32

向量化策略
==================

MLIR 中通常有两种向量化路径：

**1. 自动向量化（从 linalg 生成）**

.. code-block:: console

   $ mlir-opt --linalg-vectorize input.mlir

   // linalg.generic → vector operations

**2. 手写向量化（直接使用 Vector Dialect）**

.. code-block:: text

   // 手写 4 元素向量加法
   %v1 = vector.load %A[%i] : memref<1024xf32>, vector<4xf32>
   %v2 = vector.load %B[%i] : memref<1024xf32>, vector<4xf32>
   %sum = arith.addf %v1, %v2 : vector<4xf32>
   vector.store %sum, %C[%i] : memref<1024xf32>, vector<4xf32>

向量化的降级
==================

Vector Dialect 的降级路径：

.. code-block:: console

   # 1. 将多维向量展开为一维
   $ mlir-opt --vector-legalize-types input.mlir

   # 2. 向量形状展开（一维 → 标量或 LLVM 操作）
   $ mlir-opt --vector-lower-to-llvm-dialect input.mlir

   # 3. 完整的降级管道
   $ mlir-opt \
       --convert-vector-to-scf \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-vector-to-llvm \
       input.mlir

LLVM 中的向量化确认
========================

Vector Dialect 最终映射为 LLVM IR 中的向量类型：

.. code-block:: text

   // MLIR
   arith.addf %v1, %v2 : vector<4xf32>

   // LLVM IR
   %sum = fadd <4 x float> %v1, %v2

   // 最终可能生成（x86）：
   // vaddps %ymm0, %ymm1, %ymm2

源码走读：向量降级的两阶段策略
======================================

Vector Dialect 的降级不是一步完成的，源码中明确拆为两个阶段：

**阶段 1：多维向量合法化** —— ``VectorToSCF.cpp``
（`VectorToSCF.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/VectorToSCF/VectorToSCF.cpp>`__）

将 ``vector<2x4xf32>`` 这样的多维向量拆为嵌套循环 + 一维向量操作。
这是因为大多数硬件 SIMD 指令面向一维向量。

**阶段 2：向量 → LLVM** —— ``ConvertVectorToLLVM.cpp``
（`ConvertVectorToLLVM.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/VectorToLLVM/ConvertVectorToLLVM.cpp>`__）

将一维 ``vector<4xf32>`` 映射为 LLVM IR 的 ``<4 x float>`` 类型，
最终由 LLVM 后端的向量化 Pass 或指令选择生成 ``vaddps`` 等机器指令。

这条路径与第一卷 :ref:`chapter-05-05-vectorization` 讨论的 LLVM 自动向量化
形成互补：MLIR Vector Dialect 让开发者**显式**控制向量形状和操作，
而不完全依赖 LLVM 的 LoopVectorize 启发式分析。

向量 load/store 与内存对齐
==============================

``vector.load`` 和 ``vector.store`` 在降级时需要处理对齐要求。
如果 memref 的对齐信息不足，``VectorToLLVM`` 会插入额外的对齐断言或
降级为标量循环——这是手写向量化时必须注意的陷阱。

动手验证
==========

.. code-block:: console

   cat > /tmp/vector_add.mlir << 'EOF'
   func.func @vec_add(%a: memref<8xf32>, %b: memref<8xf32>, %c: memref<8xf32>) {
     %c0 = arith.constant 0 : index
     %v1 = vector.load %a[%c0] : memref<8xf32>, vector<4xf32>
     %v2 = vector.load %b[%c0] : memref<8xf32>, vector<4xf32>
     %sum = arith.addf %v1, %v2 : vector<4xf32>
     vector.store %sum, %c[%c0] : memref<8xf32>, vector<4xf32>
     return
   }
   EOF

   mlir-opt /tmp/vector_add.mlir \
       --convert-vector-to-llvm \
       --convert-arith-to-llvm \
       --convert-memref-to-llvm \
       --convert-func-to-llvm

检查输出中是否出现 LLVM 向量类型。若要对比 LLVM 自动向量化的结果，
可将同一逻辑用 C 编写，运行 ``clang -S -emit-llvm -O2`` 比较 IR 差异。

本章小结
========

Vector Dialect 填补了"高层循环向量化"和"底层 SIMD 指令"之间的空白。
通过显式向量类型和操作，编译器管道可以精确控制向量宽度、shuffle 模式和
归约方式——这在 GPU kernel 和 CPU SIMD 库的实现中尤为重要。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
