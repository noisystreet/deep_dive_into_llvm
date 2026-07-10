.. _chapter-05-01-optimization-overview:

======================
优化通道概述
======================

第 4 章我们了解了 Pass 框架——知道了 Pass 是什么，怎么编写一个 Pass。现在我们把
视野拉高一点：LLVM 的优化器到底是怎么工作的？当我们执行 ``clang -O2`` 时，
背后到底发生了什么？

.. admonition:: 优化管道的代价：编译器优化"翻车"史
   :class: note

   编译器优化不是免费的午餐——有时候优化器太"聪明"了，反而会引发问题。
   以下是 LLVM 优化历史上几个著名的案例：

   **1. 安全的 memset 被优化掉了**\
   一段代码用 ``memset`` 清空密钥后释放内存——结果 LLVM 发现 buffer 在 memset 之后
   不会被读取，于是 **直接把 memset 优化掉了** ！密钥残留在内存中。这推动了
   ``memset_s`` 和 ``explicit_bzero`` 等安全函数的标准化。

   **2. 死循环被删除**\
   嵌入式系统的忙等待循环 ``for (int i = 0; i < 1000000; i++);`` 如果忘了
   ``volatile`` ，编译器会发现循环体不修改外部变量，然后 **完全删除这个循环**——
   导致延迟消失、设备失控。

   **3. 整数溢出**\
   ``if (x + 100 < x)`` 的溢出检查可能被优化器直接删除，因为 C/C++ 标准说
   有符号整数溢出是"未定义行为"。编译器"认为"不会发生，于是按"不会发生"做优化。

   这些案例说明： **理解编译器优化，是写出高效且正确代码的前提** 。

.. rst-class:: center

   ``-O2`` 不是"一个优化"，它是一个由数十个 Pass 组成的 **优化管道** （pipeline）。

优化等级（Optimization Levels）
====================================

Clang/LLVM 定义了多个优化等级，每个等级对应一套 Pass 管道的组合：

.. list-table:: LLVM 优化等级
   :header-rows: 1

   * - 等级
     - clang 选项
     - 说明
     - 典型场景
   * - -O0
     - ``-O0`` （默认）
     - 不做优化，生成最直接的 IR
     - 调试、开发
   * - -O1
     - ``-O1``
     - 基本优化，编译快
     - 少量优化需求的快速构建
   * - -O2
     - ``-O2``
     - 大多数标准优化，生产级
     - 日常发布构建
   * - -O3
     - ``-O3``
     - 比 -O2 更激进
     - 计算密集型、HPC
   * - -Os
     - ``-Os``
     - 在 -O2 基础上优化代码体积
     - 嵌入式、移动端
   * - -Oz
     - ``-Oz``
     - 进一步压缩体积
     - 极致体积要求
   * - -Og
     - ``-Og``
     - 优化调试体验
     - 兼顾调试与性能

你可以通过 ``-O`` 后面跟不同的值来切换。不同等级的差异在于：

- **包含的 Pass 数量不同** ：-O1 约 30 个 Pass，-O2 约 70 个，-O3 约 80 个
- **Pass 的参数不同** ：比如内联 Pass 在 ``-O2`` 下更保守， ``-O3`` 下更激进
- **是否启用特定 Pass** ：向量化只在 ``-O3`` 下默认启用

Pass Pipeline 的组织方式
==============================

优化管道不是随便把 Pass 堆在一起，而是按照 **固定的顺序** 执行的。这个顺序有
深刻的设计考量——**每个 Pass 为后续 Pass 创造更好的优化条件** 。

一个典型的 ``-O2`` 管道大致如下：

.. figure:: /_static/figures/llvm_opt_pipeline.svg
   :align: center
   :alt: LLVM -O2 优化管道
   :width: 90%

   -O2 管道：分析 Pass → 变换 Pass → 向量化

这个顺序不是随意的：

1. **早期简化** （ ``mem2reg`` → ``instcombine`` → ``simplifycfg`` ）：清理 IR
   ，消除显而易见的冗余，为内联"减负"
2. **内联** （ ``Inliner`` ）：展开函数调用，使后续优化能跨越函数边界
3. **中端优化** （ ``GVN`` → ``SCCP`` → ``LICM`` → ``IndVarSimplify`` ）：
   在内联后的更大 IR 上做数据流分析和循环优化
4. **后端准备** （ ``simplifycfg`` → ``DCE`` ）：清理优化过程中产生的死代码和冗余分支

源码路径
==============

优化管道的实际定义在 LLVM 源码中。你可以在这里找到默认的 Pass 管道：

`llvm/lib/Passes/PassBuilderPipelines.cpp <file:///workspace/llvm-project/llvm/lib/Passes/PassBuilderPipelines.cpp>`__

这个文件中定义了 ``buildO0DefaultPipeline`` 、\ ``buildO1DefaultPipeline`` 、
``buildO2DefaultPipeline`` 、\ ``buildO3DefaultPipeline`` 等函数。

以 ``buildO2DefaultPipeline`` 为例，它的大致结构是：

.. code-block:: cpp
   :caption: llvm/lib/Passes/PassBuilderPipelines.cpp（简化）

   FunctionPassManager O2Pipeline;

   // 1. 早期简化
   O2Pipeline.addPass(Mem2RegPass());
   O2Pipeline.addPass(InstCombinePass());

   // 2. 内联
   O2Pipeline.addPass(ModuleInlinerPass(InlineParams));

   // 3. 中端优化
   O2Pipeline.addPass(GVNPass());
   O2Pipeline.addPass(SCCPPass());
   O2Pipeline.addPass(LICMPass());
   O2Pipeline.addPass(IndVarSimplifyPass());

   // 4. 后端清理
   O2Pipeline.addPass(SimplifyCFGPass());
   O2Pipeline.addPass(DCEPass());

查看当前管道的工具
======================

你可以用 ``opt`` 查看 clang 实际使用了哪些 Pass：

.. code-block:: console

   # 查看 -O2 对应的 Pass 管道
   $ clang -O2 -mllvm -print-pipeline-passes hello.c -c 2>&1

   # 只运行特定的 Pass
   $ opt -passes='mem2reg,instcombine,gvn' input.ll -S -o output.ll

   # 查看 Pass 的执行时间统计
   $ opt -passes='default<O2>' -time-passes input.ll -S -o /dev/null

使用 ``-time-passes`` 可以了解每个 Pass 占用了多少编译时间，这对于性能调优
（无论是编译时间还是运行时间）都非常有用。

优化与调试信息的关系
==========================

一个重要的设计原则： **优化不应该破坏调试信息的完整性** 。

- 当开启 ``-g`` 选项编译时，Clang 会在 IR 中插入调试元数据
- 大多数优化 Pass 会保守地 **保留调试元数据** （通过 ``PreservedAnalyses`` 声明）
- 但也有例外：当 ``mem2reg`` 将 ``alloca`` 提升为 SSA 值时，它会插入
  ``llvm.dbg.value`` 跟踪变量值，而不是直接丢失信息

.. code-block:: llvm

   ; -O0 -g 下的 IR（调试时）
   %x = alloca i32
   store i32 42, ptr %x
   call void @llvm.dbg.declare(ptr %x, !DILocalVariable(...))

   ; -O2 -g 下的 IR（优化后）
   call void @llvm.dbg.value(metadata i32 42, !DILocalVariable(...))
   ; %x = 42 被直接优化掉了，但调试信息通过 llvm.dbg.value 保留

在 ``-O0`` 下调试体验最好，因为 IR 结构和源码一一对应；
在 ``-O2`` 下也可以断点调试，但执行顺序可能与源码不同（因为指令重排和函数内联）。
