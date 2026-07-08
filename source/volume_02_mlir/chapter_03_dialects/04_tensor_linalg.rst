.. _mlir-03-03-04:

==========================
tensor / linalg Dialect
==========================

``tensor`` 和 ``linalg`` 是 MLIR 中用于**张量计算**和**线性代数**的核心 Dialect。
它们在机器学习编译器中扮演着重要角色——深度学习模型中的大多数计算最终会
以 ``linalg`` 操作的形式出现。

.. rst-class:: center

   ``linalg`` 的设计哲学：不是为每个线性代数操作定义单独的操作，而是提供
   一个**通用的结构化操作模板** （``linalg.generic`` ），由用户描述输入输出
   的访问模式。

tensor Dialect
===================

``tensor`` Dialect 提供了张量的定义和操作。张量是 MLIR 中最重要的高级数据类型。

**tensor 类型**

.. code-block:: text

   tensor<4xf32>                // 1D 张量（向量），4 个 f32
   tensor<4x4xf32>              // 2D 张量（矩阵），4x4 个 f32
   tensor<*xf32>                // 任意形状的 f32 张量
   tensor<4x?xf32>              // 4 行，列数动态的张量

``?`` 表示该维度是动态的（在运行时确定）。``*`` 表示所有维度都是动态的。

**tensor 操作**

.. code-block:: text

   // tensor.cast：改变张量的静态形状信息（不改变数据）
   %casted = tensor.cast %input : tensor<4xf32> to tensor<*xf32>

   // tensor.dim：获取张量在某个动态维度上的大小
   %dim = tensor.dim %tensor, %idx : tensor<4x?xf32>

   // tensor.extract：提取张量的单个元素
   %elem = tensor.extract %tensor[%i, %j] : tensor<4x4xf32>

   // tensor.insert：将单个元素插入张量
   %new_tensor = tensor.insert %elem into %tensor[%i, %j] : tensor<4x4xf32>

   // tensor.generate：通过索引生成张量
   %gen = tensor.generate %size {
       ^bb0(%i: index):
           %v = arith.index_cast %i : index to i32
           tensor.yield %v : i32
   } : tensor<?xi32>

tensor 操作的一个重要特性是：它们不涉及**内存管理**。张量是不可变的值——
每次 ``tensor.insert`` 都会产生一个新的张量值。内存分配和复用是在之后
的 **Bufferization** 阶段解决的。

linalg Dialect
===================

``linalg`` Dialect（线性代数）提供了可以**结构化的循环计算**。
它最核心的操作是 ``linalg.generic``。

**linalg.generic：通用结构化操作**

.. code-block:: text

   // element-wise 加法
   %result = linalg.generic {
       indexing_maps = [
           affine_map<(i) -> (i)>,    // %a 的索引映射
           affine_map<(i) -> (i)>,    // %b 的索引映射
           affine_map<(i) -> (i)>     // %result 的索引映射
       ],
       iterator_types = ["parallel"]  // 并行迭代
   } ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
     outs(%out : tensor<4xf32>) {
   ^bb0(%arg0: f32, %arg1: f32, %arg2: f32):
       %sum = arith.addf %arg0, %arg1 : f32
       linalg.yield %sum : f32
   } -> tensor<4xf32>

``linalg.generic`` 的核心要素：

- **indexing_maps**：每个操作数（输入和输出）的索引映射。定义了多维张量
  的每个维度如何映射到循环迭代空间
- **iterator_types**：每个循环维度的类型（``parallel``、``reduction`` 等）
- **Region**：计算内核，使用标量值进行计算

**矩阵乘法的 linalg 表示**

.. code-block:: text

   // 更高级的矩阵乘法操作
   %C = linalg.matmul ins(%A, %B : tensor<4x4xf32>, tensor<4x4xf32>)
       outs(%C_init : tensor<4x4xf32>) -> tensor<4x4xf32>

``linalg.matmul`` 等价于以下 ``linalg.generic``：

.. code-block:: text

   #map0 = affine_map<(i, j, k) -> (i, k)>
   #map1 = affine_map<(i, j, k) -> (k, j)>
   #map2 = affine_map<(i, j, k) -> (i, j)>

   %C = linalg.generic {
       indexing_maps = [#map0, #map1, #map2],
       iterator_types = ["parallel", "parallel", "reduction"]
   } ins(%A, %B : tensor<4x4xf32>, tensor<4x4xf32>)
     outs(%C_init : tensor<4x4xf32>) {
   ^bb0(%a: f32, %b: f32, %c: f32):
       %p = arith.mulf %a, %b : f32
       %s = arith.addf %c, %p : f32
       linalg.yield %s : f32
   }

注意 ``iterator_types`` 中的 ``reduction``——它表示这个维度上的运算
是归约（求和），而不是并行。

从 linalg 到 scf 的降级
===============================

``linalg`` 操作通过 **LowerToLoops** 模式转换为 ``scf``：

.. code-block:: text

   // 降级前：linalg.generic（每个操作对应多个标量运算）
   %r = linalg.generic ... -> tensor<4xf32>

   // 降级后：scf.for（显式循环）
   %r = scf.for %i = %c0 to %c4 step %c1
       iter_args(%acc = %out) -> tensor<4xf32> {
       %a_elem = tensor.extract %a[%i] : tensor<4xf32>
       %b_elem = tensor.extract %b[%i] : tensor<4xf32>
       %sum = arith.addf %a_elem, %b_elem : f32
       %new = tensor.insert %sum into %acc[%i] : tensor<4xf32>
       scf.yield %new : tensor<4xf32>
   }

这个降级由 ``linalg-generalize-named-ops`` 和 ``linalg-lower-to-loops``
Pass 完成。

Bufferization：tensor → memref
====================================

张量计算的最后一步是 **Bufferization** ——将不可变的 ``tensor`` 值转换为
可变的 ``memref`` （内存引用）。这一步解决了内存分配的问题。

.. code-block:: text

   // Bufferization 前：tensor 值
   func.func @main(%a: tensor<4xf32>, %b: tensor<4xf32>) -> tensor<4xf32> {
       %0 = linalg.add %a, %b : tensor<4xf32>
       func.return %0 : tensor<4xf32>
   }

   // Bufferization 后：memref 引用
   func.func @main(%a: memref<4xf32>, %b: memref<4xf32>, %out: memref<4xf32>) {
       linalg.add ins(%a, %b : memref<4xf32>, memref<4xf32>)
           outs(%out : memref<4xf32>)
       func.return
   }

由 ``one-shot-bufferize`` Pass 完成。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
