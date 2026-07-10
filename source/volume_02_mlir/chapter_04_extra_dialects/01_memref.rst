.. _mlir-04-04-01:

==============
memref Dialect
==============

``memref`` （Memory Reference）是 MLIR 中 **可变内存抽象** 的核心 Dialect。
它代表了 MLIR 从"值语义"（tensor）到"内存语义"（指针+布局）的转变。

.. rst-class:: center

   tensor = "值"，memref = "内存地址 + 布局描述"。
   Bufferization 做的事就是把 tensor 降级为 memref。

memref 类型结构
=======================

memref 类型不仅包含数据类型，还包含 **内存布局信息** ：

.. code-block:: text

   // 最简单的形式
   memref<4xf32>                // 一维数组，4 个 f32

   // 多维
   memref<4x4xf32>              // 二维（4 行 4 列）

   // 动态维度
   memref<?xf32>                // 一维，运行时确定长度
   memref<4x?xf32>              // 4 行，列数动态

   // 带内存空间
   memref<4xf32, 3>             // 3 = 共享内存（GPU）
   memref<4xf32, 1>             // 1 = 全局内存（GPU）

   // 带布局映射
   memref<4x4xf32, strided<[4, 1]>>
   // stride 数组说明：第 0 维步长 4，第 1 维步长 1（行主序）

在 LLVM 后端中，memref 被降级为一个 **结构化类型** ：

.. code-block:: text

   // memref<4xf32> 降级为 LLVM struct：
   !llvm.struct<(
       ptr<f32>,      // allocated pointer（分配基地址）
       ptr<f32>,      // aligned pointer（对齐后的地址）
       i64,           // offset（偏移量）
       array<1 x i64> // sizes（各维度大小）
   )>

memref 操作
==================

**分配与释放**

.. code-block:: text

   // 分配
   %m = memref.alloc() : memref<4xf32>
   %m_dynamic = memref.alloc(%size) : memref<?xf32>

   // 释放
   memref.dealloc %m : memref<4xf32>

**读写**

.. code-block:: text

   // 加载
   %val = memref.load %m[%i] : memref<4xf32>

   // 存储
   memref.store %val, %m[%i] : memref<4xf32>

   // 获取数据指针
   %ptr = memref.extract_aligned_pointer_as_index %m : memref<4xf32>
   // 返回指向 aligned pointer 的 index 类型值

**子视图（Subview）**

.. code-block:: text

   // 取子视图（不复制数据）
   %sub = memref.subview %m[%offset][%size][%stride]
       : memref<1024xf32> to memref<32xf32, strided<[1], offset: ?>>

``memref.subview`` 是零成本抽象——它不分配新内存，只产生一个新的
memref 描述符指向原缓冲区的子区域。这在图像处理、矩阵分块中非常有用。

memref 的维度与动态形状
============================

.. code-block:: text

   // 完全静态
   memref<64xf32>               // 64 个 f32，编译期已知

   // 完全动态
   memref<?xf32>                // 长度运行时确定

   // 混合
   memref<64x?xf32>             // 64 行，列数动态

使用 ``memref.dim`` 获取动态维度的大小：

.. code-block:: text

   %rows = memref.dim %m, %c0 : memref<?x?xf32>
   %cols = memref.dim %m, %c1 : memref<?x?xf32>

与 tensor 的对比
======================

.. list-table:: tensor vs memref
   :header-rows: 1

   * - 特性
     - tensor
     - memref
   * - 语义
     - 不可变值
     - 可变引用
   * - 别名
     - 无别名
     - 可以有别名
   * - 降级后
     - 消失（变为 memref）
     - LLVM struct
   * - 适用阶段
     - 高层优化
     - 低层代码生成
   * - 内存分配
     - 由 bufferization 管理
     - 显式的 alloc/dealloc

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
