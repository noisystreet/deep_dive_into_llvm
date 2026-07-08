.. _chapter-07-06-mc-layer:

=============
MC 层
=============

MC 层（Machine Code Layer）是 LLVM 后端流水线的最后一站。它将指令选择、
寄存器分配和调度后的 **MachineInstr** 转换为最终输出——**汇编文本**或**目标文件**。

.. rst-class:: center

   如果说前面的阶段在"设计指令序列"，MC 层就在"把它打印或编码出来"。

MC 层的核心抽象
====================

MC 层定义了一组与目标无关的数据结构，用于表示机器码：

.. list-table:: MC 层核心类型
   :header-rows: 1

   * - 类型
     - 说明
     - 与 MachineInstr 的对应
   * - ``MCInst``
     - 目标无关的指令表示
     - MachineInstr 的简化版本
   * - ``MCOperand``
     - 指令操作数（寄存器、立即数等）
     - MachineOperand 的简化版本
   * - ``MCSymbol``
     - 汇编标签
     - 对应 ``label:`` 或 ``.Ltmp``
   * - ``MCFixup``
     - 需要链接器修复的位置
     - 重定位信息
   * - ``MCExpr``
     - 汇编表达式
     - ``bar+4`` 这样的表达式

从 MachineInstr 到 MCInst
==============================

MachineInstr 是"编译器视图"——它包含编译器优化所需的各种信息；
MCInst 是"汇编器视图"——只包含生成目标代码所需的信息。

转换由 ``MCInstLower`` 类完成：

.. code-block:: cpp

   // X86MCInstLower.cpp（简化）
   void X86MCInstLower::lower(const MachineInstr *MI, MCInst &OutMI) {
       OutMI.setOpcode(MI->getOpcode());

       for (unsigned i = 0; i < MI->getNumOperands(); i++) {
           const MachineOperand &MO = MI->getOperand(i);
           switch (MO.getType()) {
           case MachineOperand::MO_Register:
               OutMI.addOperand(MCOperand::createReg(MO.getReg()));
               break;
           case MachineOperand::MO_Immediate:
               OutMI.addOperand(MCOperand::createImm(MO.getImm()));
               break;
           // ... 其他操作数类型
           }
       }
   }

AsmPrinter：汇编文本输出
==============================

AsmPrinter 遍历 MachineFunction，调用 MCInstLower 生成 MCInst，
然后调用 MCInstPrinter 将 MCInst 格式化为汇编文本。

.. code-block:: text

   MachineFunction → AsmPrinter → MCInstLower → MCInst → MCInstPrinter → .s 文件

流程：

1. 遍历 MachineFunction 中的所有 MachineBasicBlock
2. 遍历每个 MBB 中的所有 MachineInstr
3. 将 MachineInstr lower 为 MCInst
4. 调用 MCInstPrinter 将 MCInst 打印为汇编文本
5. 插入标签、注释、调试信息

MCInstPrinter 使用 TableGen 生成的 ``XXXGenAsmWriter.inc`` 来将每条指令
转换为汇编文本。这个文件包含一个巨大的 switch-case 表：

.. code-block:: cpp

   // 由 TableGen 自动生成
   void X86InstPrinter::printInstruction(const MCInst *MI) {
       switch (MI->getOpcode()) {
       case X86::ADD32rr:
           AsmWriter << "add\t" << getRegisterName(MI->getOperand(0).getReg())
                     << ", "   << getRegisterName(MI->getOperand(1).getReg());
           break;
       // ... 数千条 case
       }
   }

MCCodeEmitter：目标文件输出
=================================

如果 ``llc`` 的输出目标是 ``-filetype=obj`` （目标文件），则使用
MCCodeEmitter 将 MCInst 编码为二进制字节流。

.. code-block:: cpp

   // MCCodeEmitter 的接口
   class MCCodeEmitter {
       virtual void encodeInstruction(const MCInst &MI,
                                       raw_ostream &OS,
                                       SmallVectorImpl<MCFixup> &Fixups,
                                       const MCSubtargetInfo &STI) const;
   };

指令编码过程：

1. 确定指令的 opcode 和操作数编码
2. 按照目标指令格式（如 x86 的 ModRM/SIB 前缀）
   将操作数编码为二进制位
3. 输出字节流
4. 记录需要重定位的位置（MCFixup）

在 x86 中，一条 `add eax, ebx` 的编码过程：

.. code-block:: text

   add r32, r/m32 → opcode 0x01
   ModRM byte: mod=3(寄存器), reg=eax(0), r/m=ebx(3)
   → 0x01 0xC3  ← 这就是最终的机器码

MCObjectStreamer 与 MCObjectWriter
==========================================

MCCodeEmitter 生成的字节流需要按照特定目标文件格式（ELF、MachO、COFF）写入文件。
这由 MCObjectStreamer 和 MCObjectWriter 完成。

.. code-block:: text

   MCInst → MCCodeEmitter → 字节流
                           ↓
                    MCObjectStreamer
                           ↓
                    MCObjectWriter
                           ↓
                    .o 文件 (ELF/MachO/COFF)

每种目标文件格式对应一个 MCObjectWriter：

- ``ELFWObjectWriter``：ELF（Linux）
- ``MachObjectWriter``：Mach-O（macOS）
- ``WinCOFFObjectWriter``：COFF（Windows）

调试 MC 层
================

.. code-block:: console

   # 查看 MCInst 表示
   $ llc -show-mc-inst input.ll

   # 查看编码后的字节
   $ llc -show-encoding input.ll

   # 输出到目标文件
   $ llc -filetype=obj input.ll -o output.o

   # 反汇编查看
   $ llvm-objdump -d output.o

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
