.. _chapter-07-03-instruction-selection:

======================
指令选择
======================

指令选择（Instruction Selection）是将 SelectionDAG 中的目标无关节点
转换为目标相关 ``MachineInstr`` 的过程。这是后端流水线中最关键的一步。

.. rst-class:: center

   指令选择回答的问题是："IR 中的这个操作，用哪条目标指令来实现？"

SelectionDAG 指令选择
============================

传统的 LLVM 指令选择通过 SelectionDAG 完成（ISel）。

SelectionDAG 指令选择的流程：

1. **DAG 构建** ： ``SelectionDAGBuilder`` 将 IR 转换为 DAG
2. **DAGCombine** ：DAG 层面的目标无关优化
3. **合法化（Legalization）** ：将不支持的类型/操作转换为目标原生形式
4. **指令选择** ：使用 TableGen 生成的匹配表，将 DAG 节点匹配为目标指令

指令选择的核心是 **模式匹配** 。TableGen 从 ``.td`` 文件中的 ``Pattern`` 定义
生成匹配表。当 DAG 中的子图与某个指令的 Pattern 匹配时，该 DAG 子图被替换为
对应的目标指令。

.. code-block:: text

   ; .td 中的指令定义
   def ADD32rr : Instruction {
       let Pattern = [(set GR32:$dst, (add GR32:$src1, GR32:$src2))];
   }

   ; 匹配过程：
   DAG: (add GR32:$a, GR32:$b)
         ↓
   匹配 ADD32rr 的模式 (add GR32:$src1, GR32:$src2)
         ↓
   生成 MachineInstr: ADD32rr $dst, $src1, $src2

在源码中的位置：`llvm/lib/CodeGen/SelectionDAG/SelectionDAGISel.cpp <file:///workspace/llvm-project/llvm/lib/CodeGen/SelectionDAG/SelectionDAGISel.cpp>`__

FastISel：快速指令选择
============================

SelectionDAG 指令选择的代价较高——构建和优化 DAG 需要不少编译时间。
对于 ``-O0`` 编译（不优化），LLVM 使用 **FastISel**——一个轻量级的指令选择器。

FastISel 不做 DAG 构建，而是直接遍历 IR 指令，用简单的模式匹配生成
MachineInstr。它的优点是很快，缺点是无法处理复杂模式。

.. code-block:: cpp
   :caption: llvm/lib/CodeGen/SelectionDAG/FastISel.cpp

   bool FastISel::selectOperator(const Instruction *I, unsigned Opcode) {
       switch (I->getOpcode()) {
       case Instruction::Add:
           return selectAdd(I);   // 直接生成加法指令
       case Instruction::Load:
           return selectLoad(I);  // 直接生成加载指令
       // ...
       }
       return false;  // 无法处理 → 回退到 SelectionDAG
   }

如果 FastISel 遇到无法处理的指令，它会优雅地回退到完整的 SelectionDAG ISel。

在源码中的位置：`llvm/lib/CodeGen/SelectionDAG/FastISel.cpp <file:///workspace/llvm-project/llvm/lib/CodeGen/SelectionDAG/FastISel.cpp>`__

GlobalISel：新一代指令选择
=================================

**GlobalISel** 是 LLVM 正在推广的新一代指令选择框架。它解决了 SelectionDAG
的一些根本性问题：

.. list-table:: SelectionDAG vs GlobalISel
   :header-rows: 1

   * - 特征
     - SelectionDAG
     - GlobalISel
   * - 数据结构
     - 函数范围内的 DAG
     - 整个函数的 MIR（Machine IR）
   * - 合法化时机
     - 在指令选择前一次完成
     - 分阶段（类型/操作分开）
   * - 指令选择
     - DAG 模式匹配（TableGen）
     - TableGen 匹配 + 组合
   * - -O0 路径
     - FastISel（独立实现）
     - 同一框架的简化路径
   * - 可扩展性
     - 添加新操作需要修改 DAG
     - 更易添加新目标

GlobalISel 的流水线分为四个阶段：

.. mermaid::

   flowchart LR
       A[LLVM IR] --> B[IRTranslator\nIR → MIR]
       B --> C[Legalizer\n合法化]
       C --> D[RegisterBankSelect\n寄存器类型选择]
       D --> E[InstructionSelect\n指令选择]
       E --> F[MachineInstr]

       style A fill:#4caf50,color:#fff
       style F fill:#ff9800,color:#fff

1. **IRTranslator** ：将 LLVM IR 转换为通用的 MIR（ ``G_ADD`` 、 ``G_LOAD`` 等通用操作码）
2. **Legalizer** ：将不支持的类型/操作合法化（可以增量进行）
3. **RegisterBankSelect** ：为每个虚拟寄存器分配"寄存器类型"（如 GPR、FPR）
4. **InstructionSelect** ：将通用 MIR 指令匹配为目标特定指令

GlobalISel 在 AArch64 后端已经成熟，并在逐步推广到其他架构。在未来，
它有可能完全取代 SelectionDAG。

在源码中的位置：`llvm/lib/CodeGen/GlobalISel/ <file:///workspace/llvm-project/llvm/lib/CodeGen/GlobalISel/>`__

指令选择后：MachineInstr
==============================

指令选择的输出是 **MachineInstr**——LLVM 后端对目标指令的抽象表示。

.. code-block:: cpp

   // MachineInstr 的核心接口
   class MachineInstr {
       unsigned Opcode;                    // 指令操作码（如 X86::ADD32rr）
       SmallVector<MachineOperand, 4> Operands; // 操作数
       MachineBasicBlock *Parent;          // 所属基本块
       DebugLoc DL;                        // 调试位置
       // ... 标志位、内存描述等
   };

操作数可以是：

- **物理寄存器** （\ ``%eax`` 、\ ``%xmm0``\ ）
- **虚拟寄存器** （\ ``%vreg0`` 、\ ``%vreg1``\ ）
- **立即数** （\ ``$42`` 、\ ``$label``\ ）
- **全局地址** （\ ``@global_var``\ ）
- **栈对象** （\ ``%stack.0``\ ）

不同的操作数类型用 ``MachineOperand`` 的 ``getType()`` 区分：

.. code-block:: cpp

   switch (MO.getType()) {
   case MachineOperand::MO_Register:
       MO.getReg();           // 获取寄存器编号
       break;
   case MachineOperand::MO_Immediate:
       MO.getImm();           // 获取立即数
       break;
   case MachineOperand::MO_GlobalAddress:
       MO.getGlobal();        // 获取全局变量
       break;
   }
