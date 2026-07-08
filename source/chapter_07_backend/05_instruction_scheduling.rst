.. _chapter-07-05-instruction-scheduling:

======================
指令调度
======================

指令调度（Instruction Scheduling）是在不改变程序语义的前提下，**重新排列
指令的执行顺序**，以更好地利用 CPU 的指令级并行（ILP）能力。

.. rst-class:: center

   寄存器分配让数据在正确的寄存器里，指令调度让数据在正确的时钟周期到达。

为什么需要指令调度？
==========================

现代 CPU 不是一条接一条地执行指令，而是采用**流水线** （pipeline）技术：
多条指令的不同阶段同时执行。如果两条相邻指令争用同一个功能单元，就会产生
**停顿** （stall），浪费时钟周期。

.. code-block:: text

   不调度（有停顿）：
     add  %eax, %ebx     ; 占用 ALU，1 周期
     add  %ecx, %edx     ; 也占用 ALU → stall 等待
     load (%esi), %eax   ; 访存不占用 ALU

   调度后（无停顿）：
     add  %eax, %ebx     ; 占用 ALU
     load (%esi), %eax   ; 访存与 ALU 并行
     add  %ecx, %edx     ; ALU 空闲 → 执行

LLVM 的指令调度流水线
================================

LLVM 后端在**两个阶段**执行指令调度：

.. mermaid::

   flowchart LR
       A[指令选择] --> B[Pre-RA Scheduling]
       B --> C[寄存器分配]
       C --> D[Post-RA Scheduling]
       D --> E[MC 层发射]

       style B fill:#4a9eff,color:#fff
       style D fill:#4a9eff,color:#fff

**Pre-RA Scheduling（寄存器分配前调度）：**

在寄存器分配前进行。此时指令还在使用虚拟寄存器，调度器可以自由移动指令。
目标是**减少寄存器压力**和**提高 ILP**。

**Post-RA Scheduling（寄存器分配后调度）：**

在寄存器分配后进行。此时物理寄存器已经确定，调度器不能再移动涉及物理寄存器的指令
（除非它能处理寄存器重命名）。目标是在**不增加寄存器压力**的前提下提高 ILP。

ScheduleDAG
================

调度器的核心数据结构是 **ScheduleDAG**——表示指令间数据依赖关系的 DAG。

.. code-block:: text

   %r1 = add %r2, %r3          ; 定义 %r1
   %r4 = load (%r5)            ; 定义 %r4
   %r6 = add %r1, %r4          ; 依赖 %r1 和 %r4
   store %r6, (%r7)            ; 依赖 %r6

对应的 ScheduleDAG：

.. code-block:: text

   [add %r2, %r3]  [load (%r5)]
          \            /
           \          /
            [add %r1, %r4]
                 │
            [store %r6, (%r7)]

在 DAG 中，如果指令 B 依赖指令 A 的结果，则有一条从 A 到 B 的边。
调度器在保持这些依赖关系的前提下，可以自由重排没有依赖关系的指令。

在源码中的位置：`llvm/include/llvm/CodeGen/ScheduleDAG.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAG.h>`__

调度策略
============

LLVM 实现了多种调度策略，通过 ``-misched`` 选项选择：

.. list-table:: LLVM 调度策略
   :header-rows: 1

   * - 策略
     - 选项
     - 特点
   * - ILP（默认）
     - ``-misched=ilp``
     - 最大化指令级并行
   * - 线性化
     - ``-misched=linearize``
     - 保持指令顺序
   * - VLIW
     - ``-misched=vliw``
     - 针对 VLIW 架构优化
   * - 源顺序
     - ``-misched=source``
     - 保持源码顺序

每种调度策略都基于**启发式算法**：

.. code-block:: cpp

   // 关键路径调度：优先执行"最长的路径"上的指令
   // 因为长路径决定了总执行时间
   unsigned SchedPriority = 0;
   if (isOnCriticalPath(N))
       SchedPriority += CriticalPathBonus;
   if (hasHighRegisterPressure(N))
       SchedPriority -= RegPressurePenalty;

MachinePipeliner（循环流水线）
=====================================

**MachinePipeliner** 是一种高级调度技术，专门针对循环进行优化。
它通过**软件流水线** （software pipelining）技术，将循环的不同迭代重叠执行。

.. code-block:: text

   普通循环：
   iter 1: A1  B1  C1  D1
   iter 2:     A2  B2  C2  D2
   iter 3:         A3  B3  C3  D3

   软件流水线后：
   iter 1: A1  B1  C1  D1
   iter 2:     A2  B2  C2  D2
   iter 3:         A3  B3  C3  D3
            ──────────────→
            A1 A2 A3 同时执行？不，
            但不同迭代的不同阶段重叠执行：
            周期 1: A1
            周期 2: A2 + B1
            周期 3: A3 + B2 + C1  ← 三条指令来自三个不同迭代

软件流水线通过重叠不同迭代的执行阶段，大幅提高循环的吞吐量。但它的实现
非常复杂，目前只在少数架构（Hexagon、AMDGPU）的后端中启用。

调试指令调度
================

.. code-block:: console

   # 查看调度前的指令序列
   $ llc -stop-after=post-rasched input.ll

   # 查看调度后的指令序列
   $ llc -start-after=post-rasched input.ll

   # 查看调度 DAG
   $ llc -view-sched-dags input.ll

   # 禁用调度（用于对比）
   $ llc -pre-RA-sched=source input.ll -o output.unsched.s

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
