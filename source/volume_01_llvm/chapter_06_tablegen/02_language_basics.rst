.. _chapter-06-02-language-basics:

==========================
TableGen 语言基础
==========================

TableGen 的语法看起来有点像 C++ 和 JSON 的混合体。它的核心概念很少，
学起来比通用编程语言快得多。

.. rst-class:: center

   TableGen 程序的全部输出是 **一组记录** （records）。每一条 ``def`` 语句
   创建一个记录，每个记录是一组 ``name : value`` 的键值对。

一个最小示例
================

.. code-block:: text

   // 最简单的 TableGen 文件
   def X : SomeClass {
       let a = 42;
       let b = "hello";
   }

这就是一个完整的 TableGen 程序。它定义了一个名为 ``X`` 的记录，
包含两个字段： ``a = 42`` 和 ``b = "hello"`` 。这个记录本身没有实际意义——
它需要一个 C++ 后端来消费它。

基本语法规则
================

**注释：**

.. code-block:: text

   // 单行注释
   /* 多行注释 */
   # 这也是单行注释（类似 Python 风格）

**标识符：**

- 以字母或 ``_`` 开头，后接字母、数字、 ``_``
- 大小写敏感
- ``X`` 、 ``myReg`` 、 ``ADD32rr`` 都是合法的标识符

类型系统
============

TableGen 的类型系统很小，只有 6 种基本类型：

.. list-table:: TableGen 类型系统
   :header-rows: 1

   * - 类型
     - 字面量示例
     - 说明
   * - ``bit``
     - ``0`` 、 ``1`` 、 ``?``
     - 单个二进制位， ``?`` 表示未初始化
   * - ``bits<N>``
     - ``{0, 1, 0, 1}``
     - 固定宽度的位向量
   * - ``int``
     - ``42`` 、 ``-1`` 、 ``0xFF``
     - 整数（任意精度）
   * - ``string``
     - ``"hello"``
     - 字符串
   * - ``code``
     - ``[{ ... }]``
     - C++ 代码片段（保持原样插入）
   * - ``dag``
     - ``(add, $a, $b)``
     - 有向无环图节点（后详）
   * - ``list<type>``
     - ``[1, 2, 3]``
     - 列表（所有元素类型相同）
   * - ``Class`` 或 ``Def``
     - ``MyClass<arg1, arg2>``
     - 记录引用（指向另一个 def 或 class）

变量与 let 绑定
====================

在 TableGen 中，你可以用 ``let`` 来绑定字段的值：

.. code-block:: text

   // 基本用法
   def Y : SomeClass {
       let field1 = 10;
       let field2 = "world";
   }

   // 在外层用 let 批量设置（类似 with 语句）
   let field1 = 20, field2 = "batch" in {
       def A : SomeClass;
       def B : SomeClass;
   }
   // A 和 B 都继承了 field1=20, field2="batch"

``let`` 的作用域可以嵌套，内层覆盖外层。

多值域（VarLenField）
========================

有些指令的操作数数量不固定（比如可变参数指令）。TableGen 用 ``VarLenField``
来处理：

.. code-block:: text

   def vararg_inst : Instruction {
       let OutOperandList = (outs GPR:$dst);
       let InOperandList = (ins variable_ops);  // 可变操作数
   }

``variable_ops`` 是一个特殊标记，表示"可变数量的操作数"。

include 与文件组织
=======================

和 C/C++ 一样，TableGen 用 ``include`` 来组织文件：

.. code-block:: text

   // 包含目标架构的基本定义
   include "llvm/Target/Target.td"

   // 包含其他 .td 文件
   include "X86RegisterInfo.td"
   include "X86InstrInfo.td"

典型的 ``.td`` 文件组织层次：

.. code-block:: text

   llvm/lib/Target/X86/
   ├── X86.td                    # 顶层入口，include 所有子文件
   ├── X86RegisterInfo.td        # 寄存器定义
   ├── X86InstrInfo.td           # 指令定义
   ├── X86InstrArithmetic.td     # 算术指令
   ├── X86InstrSSE.td            # SSE 指令
   ├── X86InstrAVX.td            # AVX 指令
   ├── X86CallingConv.td         # 调用约定
   ├── X86Schedule.td            # 调度模型
   ├── X86Subtarget.td           # 处理器特性
   └── X86ISelDAGToDAG.td       # 指令选择模式

名字拼接（Paste Operator）
==============================

TableGen 支持用 ``#`` 操作符拼接标识符和字符串：

.. code-block:: text

   // 标识符拼接
   def ADD#i : Instruction { ... }  // 生成 ADD i

   // 字符串拼接
   let Description = "Add" # " " # "Operation";

这在生成大量命名相似的指令时非常有用（如 ``ADD8rr`` 、\ ``ADD16rr`` 、\ ``ADD32rr`` ）。

foreach：批量生成
===================

用 ``foreach`` 可以批量创建类似的记录：

.. code-block:: text

   // 为 8 位、16 位、32 位、64 位各生成一条加法指令
   foreach size = [8, 16, 32, 64] in {
       def ADD#size : Instruction {
           let Size = size;
           let Assembly = "add" # size;
       }
   }

这将生成 4 条记录： ``ADD8`` 、 ``ADD16`` 、 ``ADD32`` 、 ``ADD64`` 。
注意 ``foreach`` 是在 **编译期** 展开的——TableGen 没有运行时循环。

实战练习
==============

创建一个 ``test.td`` 文件：

.. code-block:: text

   class Register<string n> {
       string Name = n;
       int Size = 32;
   }

   def RAX : Register<"rax">;
   def RBX : Register<"rbx">;
   def RCX : Register<"rcx">;

   foreach r = [RAX, RBX, RCX] in {
       def "LowByte_" # r.Name : Register<r.Name # "_low"> {
           let Size = 8;
       }
   }

执行：

.. code-block:: console

   $ llvm-tblgen -print-records test.td

输出将包含 ``RAX`` 、 ``RBX`` 、 ``RCX`` 以及它们对应的 8 位版本。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
