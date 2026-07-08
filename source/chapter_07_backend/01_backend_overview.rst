.. _chapter-07-01-backend-overview:

==========================
后端架构概述
==========================

第 5 章我们看了优化器如何将 IR 优化得更高效，第 6 章看了 TableGen 如何描述目标架构。
现在该把它们串联起来了：**LLVM 的后端（Backend）如何将优化后的 IR 转换为目标机器码？**

.. rst-class:: center

   优化器关心的是"更好的 IR"，后端关心的是"真实的硬件"。

从 IR 到机器码：后端流水线
================================

LLVM 后端将 LLVM IR 转换为目标机器码，整个过程分为**一系列明确定义的阶段**：

.. mermaid::

   flowchart LR
       A[LLVM IR] --> B[指令选择\nSelectionDAG / GlobalISel]
       B --> C[指令调度\nPre-RA Scheduling]
       C --> D[寄存器分配\nRegister Allocation]
       D --> E[指令调度\nPost-RA Scheduling]
       E --> F[MC 层\nEmission]
       F --> G[机器码 / 汇编]

       style A fill:#4a9eff,color:#fff
       style G fill:#ff9800,color:#fff

每个阶段的输入和输出：

.. list-table:: 后端各阶段的输入输出
   :header-rows: 1

   * - 阶段
     - 输入
     - 输出
     - 核心抽象
   * - 指令选择
     - LLVM IR（SelectionDAG）
     - 目标相关 MachineInstr
     - SDNode → MachineInstr
   * - 指令调度（Pre-RA）
     - 无序 MachineInstr
     - 排序后的 MachineInstr
     - ScheduleDAG
   * - 寄存器分配
     - 虚拟寄存器 MachineInstr
     - 物理寄存器 MachineInstr
     - LiveInterval、VirtRegMap
   * - 指令调度（Post-RA）
     - 已分配寄存器的 MI
     - 优化排序的 MI
     - ScheduleDAG
   * - MC 层
     - MachineInstr
     - MCInst → 汇编/字节码
     - MCInst、MCObjectWriter

后端组件与 TableGen
========================

后端的每个组件都大量依赖 TableGen 生成的 ``*Gen*.inc`` 文件：

.. list-table:: 后端组件与 TableGen 的对应关系
   :header-rows: 1

   * - 后端组件
     - C++ 基类位置
     - 使用的 TableGen 生成文件
   * - TargetMachine
     - ``llvm/include/llvm/Target/TargetMachine.h``
     - ``XXXGenSubtargetInfo.inc``
   * - TargetLowering
     - ``llvm/include/llvm/CodeGen/TargetLowering.h``
     - ``XXXGenDAGISel.inc``
   * - TargetRegisterInfo
     - ``llvm/include/llvm/CodeGen/TargetRegisterInfo.h``
     - ``XXXGenRegisterInfo.inc``
   * - TargetInstrInfo
     - ``llvm/include/llvm/CodeGen/TargetInstrInfo.h``
     - ``XXXGenInstrInfo.inc``
   * - AsmPrinter
     - ``llvm/include/llvm/CodeGen/AsmPrinter.h``
     - ``XXXGenAsmWriter.inc``
   * - AsmParser
     - ``llvm/include/llvm/MC/MCParser/AsmParser.h``
     - ``XXXGenAsmMatcher.inc``

后端目录结构（以 X86 为例）
====================================

.. code-block:: text

   llvm/lib/Target/X86/
   ├── X86.h / X86.cpp              # Target 注册、初始化
   ├── X86TargetMachine.cpp         # TargetMachine 工厂
   ├── X86Subtarget.cpp             # 处理器特性选择
   ├── X86RegisterInfo.cpp           # 寄存器描述
   ├── X86InstrInfo.cpp              # 指令信息
   ├── X86ISelLowering.cpp           # SelectionDAG Lowering
   ├── X86ISelDAGToDAG.cpp           # DAG → 机器指令
   ├── X86CallingConv.cpp            # 调用约定
   ├── X86FrameLowering.cpp          # 栈帧布局
   ├── X86AsmPrinter.cpp             # 汇编输出
   ├── X86AsmParser.cpp              # 汇编解析
   ├── X86MCInstLower.cpp            # MachineInstr → MCInst
   ├── X86InstrInfo.td               # 指令定义（TableGen）
   └── X86RegisterInfo.td            # 寄存器定义（TableGen）

每个实现 LLVM 后端的 Target 目录都遵循这个模式。如果你要为一个新 CPU 架构
实现 LLVM 后端，你需要创建这个结构中的核心文件。

TargetMachine 的作用
=======================

``TargetMachine`` 是整个后端的入口点和工厂。它根据 ``Triple`` （目标三元组）
和目标特性（Subtarget）创建后端各组件：

.. code-block:: text

   TargetMachine::getSubtargetImpl()    → TargetSubtargetInfo
   TargetMachine::getTargetLowering()   → TargetLowering
   TargetMachine::getRegisterInfo()     → TargetRegisterInfo
   TargetMachine::getInstrInfo()        → TargetInstrInfo
   TargetMachine::getFrameLowering()    → TargetFrameLowering
   TargetMachine::getMCAsmInfo()        → MCAsmInfo

``TargetMachine`` 本身是一个抽象基类，每个目标架构（X86、AArch64、RISCV 等）
都有自己的实现。

在源码中的位置：`llvm/include/llvm/Target/TargetMachine.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/Target/TargetMachine.h>`__

后端的入口：llc
====================

``llc`` 是 LLVM 后端的命令行入口。它加载 LLVM IR，实例化 TargetMachine，
然后运行后端流水线：

.. code-block:: console

   # 基本用法
   $ llc input.ll -o output.s

   # 指定目标架构
   $ llc -march=x86-64 input.ll

   # 指定处理器特性
   $ llc -march=x86-64 -mcpu=skylake input.ll

   # 查看后端各阶段的输出
   $ llc -print-after-all input.ll -o /dev/null

   # 在某个阶段停止
   $ llc -stop-after=selectiondag input.ll

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
