.. _chapter-06-04-dag-expressions:

==================
DAG 表达式
==================

DAG（有向无环图）是 TableGen 中最复杂的表达式类型，也是 **指令选择模式匹配**
的核心机制。

.. rst-class:: center

   指令选择的核心就是 DAG 模式匹配：IR 的操作以 DAG 形式表示，
   后端用 TableGen 描述的 DAG 模式来匹配。

什么是 DAG？
================

DAG 是一种树形结构，但允许节点共享子节点。在 TableGen 中，DAG 表达式的格式是：

.. code-block:: text

   (operator, arg1, arg2, ..., argN)

其中 ``operator`` 是 DAG 的根节点（通常是一条指令或 SDNode），
后面的参数是子节点。

.. code-block:: text

   // 一个表示 "add" 操作树的 DAG
   (add, $a, $b)

   // 包含多级操作
   (add, (mul, $a, $b), (load, $ptr))

DAG 在指令定义中的应用
===========================

在 ``.td`` 文件中，DAG 主要用于两个地方：

**1. 指令的输入/输出操作数**

.. code-block:: text

   def ADD32rr : Instruction {
       // outs：输出操作数（目标寄存器）
       let OutOperandList = (outs GR32:$dst);
       // ins：输入操作数（源寄存器）
       let InOperandList = (ins GR32:$src1, GR32:$src2);
       // 汇编格式
       let AsmString = "add\t{$src2, $dst|$dst, $src2}";
       // 指令编码
       let Encoding = {0x01, 0xc0};
   }

``GR32:$dst`` 表示一个类型为 ``GR32`` （32 位通用寄存器）、名字为 ``$dst``
的操作数。这是 TableGen DAG 中最常见的模式。

**2. 指令选择的匹配模式（Pattern）**

.. code-block:: text

   // 当 SelectionDAG 中出现 (add GPR32:$src1, GPR32:$src2) 时，
   // 用 ADD32rr 指令来匹配
   def ADD32rr : Instruction {
       let OutOperandList = (outs GR32:$dst);
       let InOperandList = (ins GR32:$src1, GR32:$src2);
       let Pattern = [(set GR32:$dst, (add GR32:$src1, GR32:$src2))];
   }

这里的 ``Pattern`` 是一个 DAG，表示"如果 SelectionDAG 中出现这个模式，
就用这条指令"。 ``set`` 是 TableGen 的特殊操作符，表示赋值操作。

指令模式匹配的完整流程
============================

.. mermaid::

   flowchart TD
       A[LLVM IR: %r = add i32 %a, %b] --> B[SelectionDAG 构建]
       B --> C[DAG 节点: (add, %a, %b)]
       C --> D[TableGen 生成的匹配表]
       D --> E{匹配 ADD32rr 的模式?}
       E -->|是| F[生成 ADD32rr 指令]
       E -->|否| G[尝试拆分/降级]

       style A fill:#4caf50,color:#fff
       style F fill:#ff9800,color:#fff

操作数约束与类型推断
=========================

DAG 中的操作数可以带类型约束，TableGen 用这些约束来生成类型检查代码：

.. code-block:: text

   // 寄存器类约束
   (ins GR32:$src)         // 操作数必须是 GR32 寄存器
   (ins GPR:$src)          // 操作数可以是任何通用寄存器
   (ins i32imm:$imm)       // 操作数必须是 32 位立即数
   (ins memrr:$addr)       // 操作数必须是内存地址

复杂模式匹配
=================

指令选择可以匹配非常复杂的 DAG 模式：

.. code-block:: text

   // 匹配 "load + add" 的融合模式
   def LDA_ADD : Instruction {
       let OutOperandList = (outs GR32:$dst);
       let InOperandList = (ins mem:$addr, GR32:$src2);
       let Pattern = [(set GR32:$dst,
           (add (load addr:$addr), GR32:$src2))];
       let AsmString = "lda.add\t{$src2, $addr, $dst|$dst, $src2, $addr}";
   }

这种模式匹配使得 LLVM 能生成像 x86 的 ``add mem, reg`` 这样的复合指令——
一条指令同时完成加载和加法。

``ins`` 和 ``outs`` 的特殊标记
=====================================

.. list-table:: DAG 操作数中的常见标记
   :header-rows: 1

   * - 标记
     - 含义
     - 示例
   * - ``$name``
     - 命名操作数
     - ``GR32:$dst``
   * - ``variable_ops``
     - 可变数量的操作数
     - ``(ins variable_ops)``
   * - ``ops``
     - 操作数列表的别名
     - ``(outs ops:$dst)``

实战：查看 DAG 模式
========================

.. code-block:: console

   # 查看 X86 后端的指令选择模式
   $ llvm-tblgen -gen-dag-isel X86.td -o X86GenDAGISel.inc

   # 查看生成的匹配表（非常大！）
   $ head -100 X86GenDAGISel.inc

   # 用 -print-records 查看解析后的 DAG
   $ llvm-tblgen -print-records X86InstrInfo.td | grep "Pattern"
