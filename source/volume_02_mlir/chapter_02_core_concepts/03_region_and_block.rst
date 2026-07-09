.. _mlir-02-02-03:

======================
Region 与 Block
======================

在 MLIR 中，**Region** （区域）和 **Block** （块）构成了操作间的嵌套结构。
如果说 Operation 是 MLIR 的"指令"，那 Region 和 Block 就是 MLIR 的"作用域"。

.. rst-class:: center

   LLVM IR 的 BasicBlock 只能出现在函数中；MLIR 的 Block 可以出现在任何
   Operation 的 Region 中——这允许了嵌套控制流、lambda 等结构的直接表示。

.. admonition:: Region 与 SESE：结构化控制流的基石
   :class: note

   结构化控制流的核心思想是 ``SESE`` （Single Entry, Single Exit）——
   每个控制流区域只有一个入口和一个出口。``scf.for`` 的循环体就是一个
   SESE Region：从 ``scf.for`` 进入，从 ``scf.yield`` 退出。

   MLIR 的 Region 比 LLVM BasicBlock 更灵活：``scf.if`` 有两个 Region
   （then/else），Region 内还可以嵌套含 Region 的 Op。这让前端可以直接
   表示 lambda、协程、GPU kernel 等结构，而不必先展平为 goto 面条代码。

   代价是分析更复杂——MLIR 为此引入了 ``RegionBranchOpInterface`` 等
   机制，让优化器仍能推断 Region 之间的控制流边。

Block（块）
==============

**Block** 是一个有序的 Operation 序列，以**终止操作** （terminator）结尾：

.. code-block:: text

   // Block 的基本结构
   ^block_name(%arg0: i32, %arg1: f64):
       %v = arith.addi %arg0, %arg0 : i32
       arith.return %v : i32          // 终止操作

每个 Block 包含：

1. **标签** （可选）：如 ``^block_name``，用于其他 Block 引用
2. **Block 参数** （``%arg0``、``%arg1`` ）：从控制流入点传递的值
3. **Operation 序列**：按顺序执行的指令
4. **终止操作**：Block 的最后一条 Operation，决定控制流的去向

如果没有指定标签，MLIR 会为 Block 分配隐式标签：

.. code-block:: text

   func.func @main() {
       // ^bb0（隐式标签）
       %c = arith.constant 42 : i32
       return
   }

Region（区域）
==================

**Region** 是包含一个或多个 Block 的容器。每个 Region 属于且仅属于一个 Operation：

.. code-block:: text

   // scf.if 操作包含两个 Region：
   // - then Region（包含一个 Block）
   // - else Region（包含一个 Block）
   %result = scf.if %cond -> i32 {
       // then Region
       %x = arith.constant 1 : i32
       scf.yield %x : i32
   } else {
       // else Region
       %y = arith.constant 2 : i32
       scf.yield %y : i32
   }

Region 的特性：

- Region 可以包含一个或多个 Block（第一个 Block 是入口 Block）
- Region 内的 Block 通过终止操作建立控制流关系
- 一个 Operation 可以有 0 个、1 个或多个 Region（如 ``func.func`` 有一个 Region，
  ``scf.if`` 有两个 Region）

Graph Region vs SSACFG Region
=================================

MLIR 有两种 Region 模式：

.. list-table:: Region 类型
   :header-rows: 1

   * - 特征
     - SSACFG Region
     - Graph Region
   * - Block 间控制流
     - 显式（通过终止操作跳转）
     - 无（单个 Block）
   * - 控制流语义
     - 顺序执行
     - 无特定顺序（数据流驱动）
   * - 典型用途
     - 函数体、循环体
     - MLIR 中的操作图
   * - 示例
     - ``func.func``、``scf.for``
     - ``graph.op``

绝大多数 Dialect 使用 SSACFG Region。

Block 之间的控制流
=========================

当一个 Region 有多个 Block 时，Block 之间通过终止操作（terminator）建立
控制流关系：

.. code-block:: text

   func.func @example(%n: i32) -> i32 {
       // ^bb0: 入口 Block
       %c0 = arith.constant 0 : i32
       %c1 = arith.constant 1 : i32
       cf.cond_br %cond, ^bb1, ^bb2(%c0 : i32)
       //       ^^^^^^^^^  ^^^^^
       //       条件为真→bb1  条件为假→bb2，传递 %c0

   ^bb1:
       %v1 = arith.addi %n, %c1 : i32
       cf.br ^bb2(%v1 : i32)           // 无条件跳转到 bb2

   ^bb2(%arg: i32):
       return %arg : i32
   }

MLIR 使用 ``cf`` Dialect 的 ``cf.br`` 和 ``cf.cond_br`` 来表示基本的控制流，
而 ``scf`` Dialect 则提供了更高级的结构化控制流（``scf.for``、``scf.if`` ）。

Region 的嵌套
====================

Region 可以嵌套——一个 Operation 的 Region 中可以包含其他带 Region 的 Operation。
这允许了嵌套循环、嵌套条件等结构：

.. code-block:: text

   func.func @main(%A: memref<4x4xf32>, %B: memref<4x4xf32>) {
       // 外层 Region（scf.for）
       scf.for %i = %c0 to %c4 step %c1 {
           // 内层 Region（另一个 scf.for）
           scf.for %j = %c0 to %c4 step %c1 {
               %v = memref.load %A[%i, %j] : memref<4x4xf32>
               memref.store %v, %B[%i, %j] : memref<4x4xf32>
           }
       }
       return
   }

Region 在 Lowering 过程中的变化
====================================

在渐进降级过程中，Region 的结构通常会从结构化变为扁平化：

.. code-block:: text

   // 开始时是结构化控制流：
   scf.for %i = %c0 to %c4 step %c1 {
       ...
   }

   // 降级后变为基本块和控制流指令：
   cf.br ^bb1

   ^bb1:  // 循环头
       %i = ...
       cf.cond_br %cond, ^bb2, ^bb3

   ^bb2:  // 循环体
       ...
       cf.br ^bb1

   ^bb3:  // 循环出口

这种转换由 **LoopToStandard Lowering** 等 Pass 完成。

源码走读：Region 与 Block 的实现
======================================

Region 定义在 `Region.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Region.h>`__ ，
Block 定义在 `Block.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Block.h>`__ 。

Region 是 Block 的容器，一个 Operation 可以拥有零个或多个 Region。
``func.func`` 有一个 Region 包含函数体；``scf.for`` 有一个 Region 包含循环体；
``scf.if`` 有两个 Region 分别包含 then/else 分支。

Block 内的 Operation 按顺序排列，Block 参数等价于 LLVM IR 的 PHI 节点——
:ref:`mlir-03-03-03` 中 scf → cf 降级时，循环携带值就是通过 Block 参数传递的。

动手验证
==========

观察 Region 结构：

.. code-block:: console

   mlir-opt examples/mlir/chapter_03_dialects/scf_sum.mlir

``scf.for`` 的循环体就是一个 Region，内含 Block 和若干 Operation。
对比 :ref:`mlir-06-06-03` 中降级后的 ``cf.br`` / ``^bb1`` 结构，
可以直观看到 Region 如何被展开为显式 CFG。

本章小结
========

Region 和 Block 让 MLIR 在保持 SSA 的同时支持结构化控制流。
这是 scf Dialect 的基础，也是 MLIR 相比 LLVM IR 的核心优势之一。
下一节 :ref:`mlir-02-02-04` 介绍位置信息与诊断系统。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
