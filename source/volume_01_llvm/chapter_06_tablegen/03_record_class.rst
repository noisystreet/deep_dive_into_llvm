.. _chapter-06-03-record-class:

==========================
Record 与 Class
==========================

TableGen 中的两个核心概念是 **Record** （记录）和 **Class** （类）。
它们的关系有点像面向对象编程中的"实例"和"类"——但也有些关键区别。

.. rst-class:: center

   ``def`` 创建 Record，``class`` 定义模板。Record 是数据，Class 是模子。

Record（记录）
================

Record 是 TableGen 中的**具体数据单元**。每一条 ``def`` 语句创建一个 Record：

.. code-block:: text

   def R0 : Register<"r0">;
   def ADD : Instruction;

一个 Record 的核心结构是：

.. code-block:: text

   Record "R0" {
       // 继承自 Register 类的所有字段
       string Name = "r0";
       int Size = 32;
       // 可能在 Record 中覆盖的值
       let Size = 64;  // 如果覆盖的话
   }

你可以把 Record 理解为**一个包含键值对的 JSON 对象**——只是这些键值对的
类型和默认值由 ``class`` 定义。

Class（类）
================

Class 是**记录的模板**——它定义了 Record 应该包含哪些字段、什么类型和默认值。

.. code-block:: text

   class Register<string name> {
       string Name = name;       // 模板参数
       int Size = 32;            // 默认值
       list<string> Aliases = []; // 空列表
   }

   // 使用这个 class 创建记录
   def RAX : Register<"rax">;
   def EAX : Register<"eax"> {
       let Size = 32;            // 覆盖默认值
       let Aliases = ["rax"];    // 设置别名
   }

``class`` 不生成输出——只有 ``def`` 语句生成的 Record 才会出现在 TableGen 的输出中。

模板参数（Template Arguments）
=================================

Class 可以接受模板参数，语法和 C++ 类似：

.. code-block:: text

   // 多个模板参数
   class Instruction<string mnemonic, bits<8> opcode> {
       string Mnemonic = mnemonic;
       bits<8> Opcode = opcode;
       int NumOperands = 0;
   }

   // 传参创建
   def ADD : Instruction<"add", 0x01>;
   def SUB : Instruction<"sub", 0x02>;

模板参数可以有默认值：

.. code-block:: text

   class Register<string name, int size = 32> {
       string Name = name;
       int Size = size;
   }

   def R0 : Register<"r0">;       // Size = 32（默认值）
   def R1 : Register<"r1", 64>;   // Size = 64

多重继承
============

TableGen 支持**多重继承**——一个 Record 可以从多个 Class 继承字段：

.. code-block:: text

   class RREntry<bits<8> o, string n> {
       bits<8> Opcode = o;
       string Name = n;
   }

   class IsAdd {
       bit IsArithmetic = 1;
   }

   // 从两个类继承
   def ADD : RREntry<0x01, "add">, IsAdd;

多个父类中的同名字段会有冲突，需要显式覆盖：

.. code-block:: text

   class A { int X = 1; }
   class B { int X = 2; }

   def C : A, B {
       let X = 3;  // 必须覆盖，否则报错
   }

继承与覆盖规则
===================

当 Record 继承 Class 时，字段的最终值由以下规则决定：

1. **模板参数**：Class 的模板参数先赋值
2. **默认值**：Class 体内的 ``let`` 设置默认值
3. **Record 体内的 let**：Record 中的 ``let`` 覆盖 Class 的默认值
4. **外层 let**：使用 ``let ... in { def ... }`` 语法设置的值

.. code-block:: text

   class C<int x, int y = 10> {
       int A = x;
       int B = y;
       int D = 0;
   }

   // 最终 Record 的值：
   // A = 5（模板参数）
   // B = 10（默认值）
   // D = 7（Record 体内覆盖）
   def R : C<5> {
       let D = 7;
   }

匿名记录与 foreach 的结合
===============================

有时候你不需要给中间 Record 命名。TableGen 允许匿名定义：

.. code-block:: text

   // 匿名记录：直接嵌入到另一个记录中
   def CPU : ProcessorModel {
       let Itineraries = ProcessorItineraries<
           [ALU, FPU],        // 功能单元
           [2, 4],            // 流水线级数
           // 匿名指令行程表条目
           [InstrItinClass<
               "ADD", [ALU], 1>,
            InstrItinClass<
               "MUL", [FPU], 3>]
       >;
   }

通过 ``foreach`` 批量创建匿名记录是常见的模式：

.. code-block:: text

   foreach i = 0-31 in {
       def R#i : Register<"r"#i>;
   }
   // 生成 R0, R1, R2, ..., R31

在源码中的位置
================

TableGen 的核心数据结构定义在 LLVM 源码中：

`llvm/include/llvm/TableGen/Record.h <file:///workspace/llvm-project/llvm/include/llvm/TableGen/Record.h>`__

``Record`` 类和 ``RecordVal`` 类分别对应 Record 和其字段：

.. code-block:: cpp

   class Record {
       std::string Name;
       std::vector<RecordVal> Values;
       std::vector<Record*> SuperClasses;
       SMLoc Loc;  // 源码位置
   };

   class RecordVal {
       StringRef Name;
       RecTy *Type;    // 类型
       Init *Value;    // 值（可能是未求值的表达式）
   };

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
