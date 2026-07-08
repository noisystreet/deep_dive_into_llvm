.. _chapter-07-02-selection-dag:

================
SelectionDAG
================

**SelectionDAG** 是 LLVM 后端指令选择阶段的核心数据结构。它将 LLVM IR
转换为一个目标无关的 DAG（有向无环图），然后逐步"lower"（降级）为目标特定的指令。

.. rst-class:: center

   SelectionDAG 是一个"翻译站"——LLVM IR 进来，目标无关的 DAG 出去，
   然后在指令选择中被匹配为具体的目标指令。

SelectionDAG 的节点结构
============================

SelectionDAG 中的每个节点是一个 ``SDNode``，节点间的边代表数据依赖关系：

.. code-block:: text

   SDNode (opcode: ISD::ADD)
     ├── operand 0: SDNode (opcode: ISD::Register, val: %a)
     └── operand 1: SDNode (opcode: ISD::Register, val: %b)

核心类型：

.. list-table:: SelectionDAG 核心类型
   :header-rows: 1

   * - 类型
     - 说明
   * - ``SDNode``
     - DAG 节点，代表一个操作
   * - ``SDValue``
     - 指向 SDNode + 输出编号（一个节点可能有多个输出）
   * - ``SDUse``
     - DAG 中的使用-定义关系
   * - ``SelectionDAG``
     - DAG 的容器，管理所有节点

从 LLVM IR 到 SelectionDAG
================================

``TargetLowering::LowerOperation`` 是 IR 到 DAG 的转换入口。以下面的 IR 为例：

.. code-block:: llvm

   %result = add i32 %a, %b

它会被转换为 SelectionDAG 中的：

.. code-block:: text

   t0: i32 = Register %a        ; 叶节点：读寄存器
   t1: i32 = Register %b        ; 叶节点：读寄存器
   t2: i32 = add t0, t1        ; 内部节点：加法

整个过程由 ``SelectionDAGBuilder`` 类完成。它遍历 LLVM IR 的 BasicBlock，
为每条 IR 指令创建对应的 ``SDNode``。

在源码中的位置：`llvm/lib/CodeGen/SelectionDAG/SelectionDAGBuilder.cpp <file:///workspace/llvm-project/llvm/lib/CodeGen/SelectionDAG/SelectionDAGBuilder.cpp>`__

DAGCombine：DAG 层面优化
==============================

在 DAG 构建后和指令选择前，LLVM 运行 **DAGCombine**——在 DAG 层面做
目标无关的优化。这是"中端优化"在后端的延续。

.. code-block:: text

   优化前：         优化后：
   (add x, 0)  →   x           （加 0 恒等）
   (mul x, 1)  →   x           （乘 1 恒等）
   (sub x, 0)  →   x           （减 0 恒等）
   (add (load p), 0) → (load p) （冗余加法消除）

DAGCombine 还处理更复杂的模式，比如将多个操作合并为一个等效操作（如
将 ``(and (shl x, C1), C2)`` 合并为更高效的形式）。

在源码中的位置：`llvm/lib/CodeGen/SelectionDAG/DAGCombiner.cpp <file:///workspace/llvm-project/llvm/lib/CodeGen/SelectionDAG/DAGCombiner.cpp>`__

Legalization：合法化
=========================

"合法化"是将 DAG 中的操作转换为目标架构原生支持的形式。合法化分为两个方面：

**类型合法化（Type Legalization）：**

如果目标架构不支持 ``i128`` 类型（比如 32 位 ARM），类型合法化会将 ``i128``
操作拆分为多个 ``i32`` 操作。

.. code-block:: text

   ; 不支持 i128 的架构
   (add i128 %a, %b)
       → 拆分为
   (add i32 %a_lo, %b_lo)
   (adde i32 %a_hi, %b_hi, carry)

**操作合法化（Operation Legalization）：**

如果目标架构没有直接的乘法指令（或者乘法指令代价极高），操作合法化会将
乘法操作展开为加法和移位。

.. code-block:: text

   ; 乘法合法化：x * 10 → (x << 3) + (x << 1)
   ; 前提是目标没有乘法指令

LLVM 定义了三种操作合法化状态：

.. code-block:: cpp

   enum LegalizeAction {
       Legal,      // 目标原生支持
       Promote,    // 类型需要扩展（如 i8 → i32）
       Expand,     // 拆分为多个操作
       Custom      // 用自定义代码处理
   };

指令选择模式匹配
======================

经过合法化后，DAG 中的操作被转换为目标原生支持的形式。接下来是**指令选择**
（Instruction Selection）——将 DAG 中的每个节点匹配为具体的目标指令。

指令选择的核心是 TableGen 生成的 ``XXXGenDAGISel.inc`` 文件。它包含一个巨大的
匹配表（通常数万行），用 switch-case 或 trie 树对 DAG 模式进行匹配。

从 SelectionDAG 的角度看，后端流水线是这样的：

.. mermaid::

   flowchart LR
       A[LLVM IR] --> B[SelectionDAGBuilder]
       B --> C[SelectionDAG]
       C --> D[DAGCombine]
       D --> E[Legalization]
       E --> F[DAGCombine 再次]
       F --> G[指令选择\nTableGen 匹配]
       G --> H[MachineInstr DAG]

       style A fill:#4caf50,color:#fff
       style H fill:#ff9800,color:#fff

SelectionDAG 的调试
=======================

.. code-block:: console

   # 查看 DAG 的各种形式
   $ llc -view-dag-combine1-dags input.ll    # DAGCombine 前的 DAG
   $ llc -view-dag-combine2-dags input.ll    # DAGCombine 后的 DAG
   $ llc -view-legalize-dags input.ll        # 合法化后的 DAG
   $ llc -view-isel-dags input.ll            # 指令选择后的 DAG

   # 文本形式输出
   $ llc -stop-after=selectiondag input.ll

   # 用 Graphviz 可视化
   $ llc -view-sched-dags input.ll

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
