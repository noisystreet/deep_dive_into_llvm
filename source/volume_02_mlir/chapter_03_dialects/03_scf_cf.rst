.. _mlir-03-03-03:

==========================
控制流 Dialect: scf / cf
==========================

MLIR 中有两个控制流 Dialect： **scf** （Structured Control Flow）提供结构化的
控制流结构； **cf** （Control Flow）提供底层的分支指令。两者的关系类似于
高级语言中的 ``for/while`` 和汇编语言中的 ``jmp/je`` 。

.. rst-class:: center

   绝大多数 MLIR 程序使用 ``scf`` 来表达控制流。 ``cf`` 只在降级的最后阶段
   出现——当结构化控制流被转换为底层分支后。

.. admonition:: scf 与 cf：编译器里的"高级语言"与"汇编"
   :class: note

   这和传统编译器前端/后端的角色分工惊人地相似：

   - **scf** ≈ 带 ``for``/``if`` 的高级语言——保留循环结构，便于分析和变换
   - **cf** ≈ 只有 ``br``/``cond_br`` 的汇编——接近 LLVM IR 的 CFG

   关键设计决策是： **优化尽量在 scf 层完成** 。循环展开、向量化、
   并行化都依赖 ``scf.for`` 的 ``iter_args`` 语义；一旦降到 cf，
   循环携带值变成 Block 参数，变换难度陡增。

   LLVM 的 Loop Pass 也面临同样困境——所以 MLIR 社区极力主张
   "在结构化层多做优化，晚一点再展平"。

scf Dialect
=================

``scf`` 提供了三种结构化控制流结构： ``scf.for`` 、 ``scf.while`` 、 ``scf.if`` 。

**scf.for：定次循环**

.. code-block:: text

   // 从 lb 到 ub，步长 step
   scf.for %i = %lb to %ub step %step {
       // 循环体
   }

   // 带迭代器累加器（reduction 模式）
   %result = scf.for %i = %c0 to %N step %c1
       iter_args(%acc = %init) -> i32 {
       %v = arith.addi %acc, %i : i32
       scf.yield %v : i32
   }

``scf.for`` 的语义： ``%i`` 从 ``%lb`` 开始，每次增加 ``%step`` ，
直到大于等于 ``%ub`` 。循环体的每次迭代通过 ``scf.yield`` 传递值给下一轮。

**scf.while：条件循环**

.. code-block:: text

   // while 循环：先判断，后执行
   %result = scf.while (%arg = %init) -> i32 {
       // before block：判断条件
       %cond = arith.cmpi slt, %arg, %limit : i32
       scf.condition(%cond) %arg : i32
   } do {
   ^bb0(%arg: i32):
       // after block：循环体
       %next = arith.addi %arg, %c1 : i32
       scf.yield %next : i32
   }

``scf.while`` 有两个 Region： ``before`` 块检查条件， ``after`` 块执行体。

**scf.if：条件分支**

.. code-block:: text

   // if-else
   %result = scf.if %cond -> i32 {
       // then 分支
       scf.yield %true_val : i32
   } else {
       // else 分支
       scf.yield %false_val : i32
   }

   // if（无 else）
   scf.if %cond {
       // 只有 then 分支
   }

``scf.if`` 的两个 Region 都返回相同类型（如果有返回值），或者都无返回值。

**scf.parallel：并行循环**

.. code-block:: text

   // 并行 for 循环
   scf.parallel (%i, %j) = (%c0, %c0) to (%N, %M) step (%c1, %c1) {
       // 循环体
       scf.yield
   }

``scf.parallel`` 的语义是：迭代之间 **没有数据依赖** ，可以并行执行。
降级时，它可以根据目标平台映射为 OpenMP 的 ``#pragma omp parallel for``
或 GPU 的线程网格。

cf Dialect
=================

``cf`` 提供了底层的控制流指令，类似于 LLVM IR 中的 ``br`` 和 ``cond_br`` 。

**cf.br：无条件跳转**

.. code-block:: text

   cf.br ^target_bb(%val0, %val1 : i32, f64)

**cf.cond_br：条件跳转**

.. code-block:: text

   cf.cond_br %cond, ^true_bb(%v1 : i32), ^false_bb(%v2 : i32)

   // 等价于 LLVM IR 的：
   // br i1 %cond, label %true_bb, label %false_bb

**cf.assert：断言**

.. code-block:: text

   cf.assert %cond, "x must be positive: %d", %x : i32

在调试模式下，如果断言失败，会打印消息并中止执行。在 Release 模式下，
断言可以被消除。

scf → cf 的降级
===================

结构化控制流最终需要降级为底层分支。以 ``scf.for`` 为例：

.. code-block:: text

   // 降级前：scf.for
   scf.for %i = %c0 to %N step %c1 {
       %v = arith.addi %acc, %i : i32
       scf.yield %v : i32
   }

   // 降级后：cf.br + cf.cond_br
   cf.br ^bb1

   ^bb1:               // 循环头
       %i = ...        // phi / block args
       %cond = arith.cmpi slt, %i, %N : i32
       cf.cond_br %cond, ^bb2, ^bb3

   ^bb2:               // 循环体
       %v = arith.addi %acc, %i : i32
       %next_i = arith.addi %i, %c1 : i32
       cf.br ^bb1(%next_i, %v : i32, i32)

   ^bb3:               // 循环出口
       ...

这个降级由 ``convert-scf-to-cf`` Pass 完成。

源码走读：scf.for 的 Region 语义
======================================

``scf.for`` 的 ODS 定义在
`SCFOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/SCF/IR/SCFOps.td>`__ 。
它实现了 ``RegionBranchOpInterface`` ——告诉 MLIR 框架这个 Op 的 Region
如何与外部控制流交互。

与 LLVM IR 的 ``phi`` 节点对比： ``scf.for`` 用 ``iter_args`` 显式声明
循环携带值，用 ``scf.yield`` 传递下一轮的状态。优化器不需要运行
支配树分析就能识别循环结构——这正是 :ref:`chapter-05-03-loop-optimizations`
中 LoopInfo 试图恢复的信息，而 scf 在 IR 层面直接保留了它。

``cf`` 的底层分支定义在
`ControlFlowOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/ControlFlow/IR/ControlFlowOps.td>`__ 。
``cf.cond_br`` 通过 Block 参数传递值，等价于 LLVM IR 的 PHI 节点语义，
但以一种更显式的 CFG 形式呈现。

源码走读：SCFToControlFlow 的不变量
======================================

降级实现详见 :ref:`mlir-11-06-03` 中分析的
`SCFToControlFlow.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/SCFToControlFlow/SCFToControlFlow.cpp>`__ 。
其核心不变量值得在此重申：生成的 CFG 子图有单一入口和单一出口，
循环携带值通过条件块的 Block 参数在所有后继块中可见。

动手验证
==========

项目提供了 scf 循环示例，文件为 ``examples/mlir/chapter_03_dialects/scf_sum.mlir`` 。

.. code-block:: console

   # 观察结构化控制流
   mlir-opt examples/mlir/chapter_03_dialects/scf_sum.mlir

   # 降级为 cf + LLVM Dialect
   mlir-opt examples/mlir/chapter_03_dialects/scf_sum.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts

第二步输出中应出现 ``cf.br`` 、 ``cf.cond_br`` 和 ``^bb1`` 等 CFG 结构——
这正是前文 scf → cf 降级示例的具体 IR 形态。

本章小结
========

scf 和 cf 体现了 MLIR 在控制流上的分层设计：scf 保留结构，cf 暴露 CFG，
最终都汇入 LLVM Dialect 的 ``llvm.br`` 。绝大多数 MLIR 程序在编写和优化阶段
使用 scf，只在降级末期才接触 cf 。

下一节 :ref:`mlir-03-03-04` 将介绍张量计算的核心 Dialect：tensor 与 linalg 。

降级路径总结
==================

.. code-block:: text

   scf.for / scf.if / scf.while
         ↓（convert-scf-to-cf）
   cf.br / cf.cond_br
         ↓（convert-cf-to-llvm）
   llvm.br / llvm.cond_br
         ↓（translate）
   LLVM IR: br / br i1

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
