.. _mlir-04-04-03:

=====================
Transform Dialect
=====================

``transform`` Dialect 是 MLIR 中最**独特**的 Dialect——它本身就是一个
**元编程** （meta-programming）的工具。你不只是用它来表达计算，而是用它来
描述"如何变换计算"。

.. rst-class:: center

   传统 Pass 是"写 C++ 代码变换 IR"，Transform Dialect 是"写 IR 变换 IR"。
   ——把 Pass 逻辑从 C++ 搬到 MLIR 里。

为什么需要 Transform Dialect？
===================================

传统的 MLIR Pass 是在 C++ 中硬编码的。如果你想调整 Pass 的顺序或参数，
必须修改 C++ 代码、重新编译、重新链接。

Transform Dialect 改变了这一切：**变换逻辑本身就是 MLIR IR**。

.. code-block:: text

   // transform 脚本：描述如何优化一个 linalg 计算
   module attributes {transform.with_named_sequence} {
       transform.named_sequence @transform_main(%arg0: !transform.any_op) {
           // 1. 匹配目标操作
           %func = transform.structured.match
               op_name("linalg.matmul") in %arg0
               : (!transform.any_op) -> !transform.any_op

           // 2. 对匹配的操作做 tiling
           %tiled, %loops = transform.structured.tile_using_for
               %func {tile_sizes = [32, 32, 16]}
               : (!transform.any_op) -> (!transform.any_op, !transform.any_op)

           // 3. 应用 vectorization
           transform.structured.vectorize %tiled
               : (!transform.any_op) -> !transform.any_op

           transform.yield
       }
   }

这个脚本可以直接用 ``mlir-opt`` 运行，无需写一行 C++。

核心概念
==============

Transform Dialect 有几个核心操作：

**匹配（Match）**

.. code-block:: text

   // 按操作名称匹配
   %ops = transform.structured.match
       op_name("linalg.add") in %target
       : (!transform.any_op) -> (!transform.any_op)

   // 按属性匹配
   %ops = transform.structured.match
       attrs{fastmath = #arith.fastmath<fast>} in %target
       : (!transform.any_op) -> (!transform.any_op)

**变换（Transform）**

.. code-block:: text

   // Tiling
   %tiled, %loops = transform.structured.tile_using_for
       %target {tile_sizes = [32, 32]}
       : (!transform.any_op) -> (!transform.any_op, !transform.any_op)

   // Fusion
   %fused = transform.structured.fuse %target
       : (!transform.any_op) -> (!transform.any_op)

   // Vectorization
   transform.structured.vectorize %target
       : (!transform.any_op) -> !transform.any_op

**控制流**

.. code-block:: text

   // 条件执行
   transform.if %cond -> !transform.any_op {
       transform.yield %true_result : !transform.any_op
   } else {
       transform.yield %false_result : !transform.any_op
   }

   // 重复执行直到收敛
   transform.repeatedly %target {
       // 应用优化直到无变化
       transform.yield %target : !transform.any_op
   }

使用场景
==============

**场景 1：可组合的 Pass Pipeline**

.. code-block:: text

   // 一个可复用的变换模块
   module @tiling_pipeline {
       transform.named_sequence @apply_tiling(%arg0: !transform.any_op) {
           %tiled, _ = transform.structured.tile_using_for
               %arg0 {tile_sizes = [64, 64]}
               : (!transform.any_op) -> (!transform.any_op, !transform.any_op)
           transform.yield %tiled : !transform.any_op
       }
   }

**场景 2：条件优化**

.. code-block:: text

   // 只有在目标设备支持 SIMD 时才向量化
   %has_simd = transform.check.isa_dialect<%target, "vector">
   transform.if %has_simd {
       transform.structured.vectorize %target
           : (!transform.any_op) -> !transform.any_op
   }

与 Pass 的对比
==================

.. list-table:: Transform Script vs C++ Pass
   :header-rows: 1

   * - 特性
     - Transform Script
     - C++ Pass
   * - 修改方式
     - 改 .mlir，无需编译
     - 改 C++，重新链接
   * - 复用性
     - 模块间可共享
     - 需链接库
   * - 调试
     - 可以用 mlir-opt 单步查看
     - 需 GDB/LLDB
   * - 表达能力
     - 受限于 Transform Op 集
     - 任意 C++ 能力
   * - 性能
     - 解释执行
     - 编译执行

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
