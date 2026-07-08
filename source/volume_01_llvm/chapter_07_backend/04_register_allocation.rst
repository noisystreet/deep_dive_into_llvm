.. _chapter-07-04-register-allocation:

======================
寄存器分配
======================

指令选择之后，MachineInstr 中使用的仍然是**虚拟寄存器** （virtual registers）。
虚拟寄存器数量无限，而物理寄存器数量有限。**寄存器分配** （Register Allocation）
的任务就是：**将无限多的虚拟寄存器映射到有限的物理寄存器上**。

.. rst-class:: center

   如果没有寄存器分配，编译器就退回到了"所有变量都在内存中"的时代。
   寄存器分配是编译器优化中最有影响力的环节之一。

寄存器分配的核心问题
========================

.. code-block:: text

   假设有 5 个虚拟寄存器 %vreg0 ~ %vreg4，但目标只有 3 个物理寄存器。
   哪些虚拟寄存器应该占用寄存器？哪些应该被"溢出"（spill）到内存？

   -------- 时间轴 -------->
   %vreg0:  ██████████░░░░░░░░░░░░░░░
   %vreg1:  ░░██████████░░░░░░░░░░░░░
   %vreg2:  ░░░░░░██████████░░░░░░░░░
   %vreg3:  ░░░░░░░░░░█████████░░░░░░
   %vreg4:  ░░░░░░░░░░░░░░░░░████████
                                  ↑ 这里需要 3 个寄存器，
                                   但只有 %vreg0 和 %vreg1 不再被使用，
                                   %vreg3 还在用，需要 spill

核心概念：**LiveInterval（活跃区间）**

每个虚拟寄存器从被定义开始，到最后一次使用为止，这段时间称为它的"活跃区间"。
寄存器分配器需要确保在同一时间点活跃的虚拟寄存器数量不超过物理寄存器数量。

.. code-block:: cpp

   // LiveInterval 表示一个寄存器的活跃范围
   class LiveInterval {
       unsigned Reg;                      // 寄存器编号
       SmallVector<LiveRange, 4> Ranges; // 活跃范围列表
       // 每个 LiveRange 包含多个 Segment（段）
       struct Segment {
           SlotIndex Start;  // 开始位置
           SlotIndex End;    // 结束位置
       };
   };

LLVM 的寄存器分配器
===========================

LLVM 实现了多个寄存器分配器，通过 ``-regalloc`` 选项选择：

.. list-table:: LLVM 寄存器分配器
   :header-rows: 1

   * - 名称
     - 命令行选项
     - 特点
     - 使用场景
   * - **Greedy**
     - ``-regalloc=greedy`` （默认）
     - 基于贪心算法，质量高
     - 生产环境默认
   * - **Basic**
     - ``-regalloc=basic``
     - 线性扫描，速度快
     - -O0 快速编译
   * - **Fast**
     - ``-regalloc=fast``
     - 极简分配
     - 调试

**Greedy 分配器** 的工作流程：

1. 计算所有虚拟寄存器的 LiveInterval
2. 按活跃区间长度排序（最长的先分配）
3. 为每个虚拟寄存器尝试分配物理寄存器
4. 如果冲突，尝试**拆分（split）**活跃区间（在冲突点拆分）
5. 如果拆分后仍无法分配，将变量**溢出（spill）**到内存

.. code-block:: text

   分配前：
   %vreg0 = ...       （需要 %eax 或 %ebx 或 %ecx）
   %vreg1 = ...
   %vreg2 = ...

   分配后：
   %eax = ...         （%vreg0 → %eax）
   %ebx = ...         （%vreg1 → %ebx）
   // %vreg2 的活跃区间与 %eax 不重叠 →
   // 可以复用 %eax
   %eax = ...         （%vreg2 → %eax）

Spilling：溢出
====================

当物理寄存器不够时，分配器将某些虚拟寄存器的值**溢出到内存** （spill）。
这会引入额外的 ``load`` 和 ``store`` 指令。

.. code-block:: text

   溢出前：
     %vreg0 = add %vreg1, %vreg2     ; 都在寄存器里

   溢出后（%vreg2 被 spill）：
     store %vreg2, %spill_slot        ; spill：存到栈上
     %vreg0 = add %vreg1, %vreg2      ; %vreg1 仍在寄存器中
     ...
     %vreg2 = load %spill_slot        ; reload：从栈上加载回来

Spilling 会降低性能（访存比寄存器操作慢得多），所以分配器的核心目标就是
**最小化溢出**。

Register Coalescing（寄存器合并）
=======================================

在指令选择过程中，经常会生成多余的 ``copy`` 指令（寄存器间的数据移动）。
**Register Coalescing** 尝试消除这些 copy：

.. code-block:: text

   合并前：
     %vreg0 = copy %vreg1      ; 复制
     ... = use %vreg0

   合并后：
     ... = use %vreg1          ; 直接使用原始值
     ; copy 指令被消除，%vreg0 与 %vreg1 共享物理寄存器

合并不只是优化，它还能**减少虚拟寄存器的数量**，从而降低寄存器分配的压力。

在源码中的位置：`llvm/lib/CodeGen/RegisterCoalescer.cpp <file:///workspace/llvm-project/llvm/lib/CodeGen/RegisterCoalescer.cpp>`__

寄存器提示（Hint）
======================

某些指令对操作数的寄存器有特殊要求。例如 x86 的除法指令 ``div`` 要求
被除数在 ``%eax``/``%rdx`` 中。这种约束通过**寄存器提示** （Register Hint）
传递给分配器：

.. code-block:: cpp

   // 在 TargetInstrInfo 中设置寄存器约束
   unsigned getRegForInlineAsmConstraint(...) {
       // 返回必须使用的物理寄存器编号
   }

   // 分配器优先满足有提示的虚拟寄存器
   // 如果无法满足提示，再尝试其他寄存器

调试寄存器分配
====================

.. code-block:: console

   # 查看分配后的寄存器分配
   $ llc -print-after=regalloc input.ll

   # 使用不同的分配器对比
   $ llc -regalloc=greedy input.ll -o output.greedy.s
   $ llc -regalloc=basic input.ll -o output.basic.s

   # 查看 spilling 统计
   $ llc -stats input.ll

   # 调试分配过程
   $ llc -debug-only=regalloc input.ll

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
