.. _chapter-06-01-tablegen-intro:

==================
TableGen 概述
==================

如果你读过 LLVM 后端的源码，一定会注意到大量的 ``.td`` 文件——它们遍布在每个
Target 目录下（``X86.td`` 、\ ``AArch64.td`` 、\ ``RISCV.td`` 等）。这些文件用
一种叫 **TableGen** 的声明式语言编写。

.. rst-class:: center

   TableGen 的核心思想：**用声明式描述代替手写代码**——你描述"有什么"，
   编译器自动生成"怎么做"。

TableGen 要解决的问题
========================

后端代码生成中有大量重复、机械的工作。以指令集描述为例，你需要为每条指令写：

- 指令编码（opcode、machine code bit layout）
- 汇编语法（mnemonic、operand formatting）
- 指令选择模式（如何匹配 IR 指令）
- 反汇编信息
- 调试信息

在传统的编译器（如 GCC）中，这些信息散布在不同的文件中，需要手动维护一致性。
修改一条指令意味着要同步修改四五处代码。

TableGen 的做法是：**用一份 ``.td`` 文件集中描述指令的所有属性**，然后由
不同的 TableGen 后端（TableGen Backend）自动生成各种代码文件。

.. mermaid::

   flowchart LR
       A[.td 文件\n声明式描述] --> B[llvm-tblgen]
       B --> C[XXXGenInstrInfo.inc\n指令编码/解码]
       B --> D[XXXGenRegisterInfo.inc\n寄存器描述]
       B --> E[XXXGenAsmWriter.inc\n汇编输出]
       B --> F[XXXGenAsmMatcher.inc\n汇编匹配]
       B --> G[XXXGenDAGISel.inc\n指令选择模式]

       style A fill:#ff9800,color:#fff
       style B fill:#4a9eff,color:#fff

哪些代码是 TableGen 生成的？
===================================

在 LLVM 的构建目录中搜索 ``*Gen*.inc`` 文件，可以找到所有由 TableGen 生成的
C++ 代码。以下是几个关键文件及其用途：

.. list-table:: TableGen 生成的关键文件
   :header-rows: 1

   * - 生成文件名
     - 用途
     - 对应 .td 输入
   * - ``XXXGenRegisterInfo.inc``
     - 寄存器枚举、寄存器类、寄存器别名
     - ``XXXRegisterInfo.td``
   * - ``XXXGenInstrInfo.inc``
     - 指令枚举、操作数类型、指令编码
     - ``XXXInstrInfo.td``
   * - ``XXXGenDAGISel.inc``
     - SelectionDAG 指令选择匹配器
     - ``XXXInstrInfo.td`` + ``XXXISelDAGToDAG.td``
   * - ``XXXGenAsmWriter.inc``
     - 汇编打印（指令 → 汇编文本）
     - ``XXXInstrInfo.td``
   * - ``XXXGenAsmMatcher.inc``
     - 汇编匹配（汇编文本 → 指令）
     - ``XXXAsmParser.td``
   * - ``XXXGenSubtargetInfo.inc``
     - 处理器特性、调度模型
     - ``XXXSubtarget.td``
   * - ``XXXGenCallingConv.inc``
     - 调用约定实现
     - ``XXXCallingConv.td``

对于一个新后端，你编写 ``.td`` 文件后，TableGen 自动生成这些 ``.inc`` 文件，
然后 LLVM 的 C++ 代码 ``#include`` 它们。

llvm-tblgen 工具
====================

``llvm-tblgen`` 是 TableGen 的编译器。它读取 ``.td`` 文件并输出各种格式。

.. code-block:: console

   # 查看生成的记录列表
   $ llvm-tblgen -print-records X86.td

   # 生成指令信息
   $ llvm-tblgen -gen-instr-info X86InstrInfo.td -o X86GenInstrInfo.inc

   # 查看所有可用的生成器（backend）
   $ llvm-tblgen --help | grep gen

常用生成器包括：``-gen-instr-info``、``-gen-register-info``、``-gen-dag-isel``、
``-gen-asm-writer``、``-gen-asm-matcher``、``-gen-subtarget`` 等。

TableGen 不是通用语言
=========================

TableGen **不是** 像 C++ 或 Python 那样的通用编程语言。它没有循环（有 ``foreach``
但本质是编译期展开）、没有函数调用（有多态继承和模板参数）、没有运行时控制流。

TableGen 是一个**数据描述语言** ——它的全部输出就是一组**记录** （Records），
每个记录是一组键值对。C++ 代码再根据这些记录生成实际的代码。

这也意味着：**TableGen 中没有逻辑计算**。你能做的就是用继承、多态和模板参数
来组织和复用数据描述。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
