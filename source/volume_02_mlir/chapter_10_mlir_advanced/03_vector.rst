.. _mlir-10-10-03:

===================
Vector Dialect
===================

Vector Dialect 是 MLIR 中用于**显式向量化**的 Dialect。它提供了丰富的
向量操作，可以精确控制 SIMD 指令的生成。

.. rst-class:: center

   Vector Dialect 的设计目标：提供硬件无关的向量抽象，同时保留足够的
   SIMD 语义让后端生成高效的向量指令。

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
