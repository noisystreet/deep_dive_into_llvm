.. _chapter-02-01-ir-basics:

==========================
IR 基础语法
==========================

第 1 章中我们使用 ``clang -S -emit-llvm`` 生成过 LLVM IR，看到了一些类似汇编的
文本。但 IR 到底是什么？它的语法规则和设计思路是怎样的？这一节我们从最基础的
层面来剖析 LLVM IR。

LLVM IR 的三种形式
========================

.. admonition:: SSA 形式的革命
   :class: note

   今天 LLVM IR 最核心的设计——**SSA（Static Single Assignment）形式**——
   最初是 IBM 的 Ron Cytron 等人在 1989 年一篇 POPL 论文中提出的理论概念。
   这篇论文的标题是 *"An Efficient Method of Computing Static Single Assignment Form"*，
   它解决了传统数据流分析中变量多次赋值导致的复杂性。

   2000 年，Chris Lattner 选择 SSA 作为 LLVM IR 的基础形式时，这是个冒险的决定。
   当时的编译器要么使用更简单的三地址码（如 Java bytecode、C--），要么使用
   更复杂的程序依赖图（PDG）。SSA 虽然理论优雅，但**实际编译器中成功应用**
   的案例还不多。

   SSA 最终被证明是 LLVM 最成功的设计决策之一：
   - **简化优化** ：每个变量只赋值一次，数据流分析变得直截了当
   - **phi 节点** ：优雅地处理控制流汇合点的值合并
   - **内存升级** ：内存上的 SSA 形式（MemorySSA）进一步将优化范围扩展到堆操作

   今天，从 LLVM IR 到 MLIR，从 WebAssembly 到 GPU 中间表示——SSA 已经
   成为现代编译器的标准设计。回过头来看，Lattner 当年的"冒险"其实押对了宝。

LLVM IR 有**三种等价的表示形式** ，它们在语义上完全一致，只是用途不同：

.. list-table::
   :header-rows: 1

   * - 形式
     - 扩展名
     - 特点
     - 典型用途
   * - 文本形式
     - ``.ll``
     - 人类可读的汇编风格文本
     - 调试、教学、手工修改
   * - 比特码形式
     - ``.bc``
     - 紧凑的二进制格式，加载速度快
     - 链接时优化（LTO）、存储、传输
   * - 内存形式
     - (C++ 对象)
     - ``llvm::Module`` / ``llvm::Function`` 等
     - 编译器内部操作

三种形式可以无损转换：

.. code-block:: bash

   llvm-as hello.ll -o hello.bc    # 文本 -> 比特码
   llvm-dis hello.bc -o hello.ll   # 比特码 -> 文本

为什么需要三种？想象一个场景：Clang 编译 ``foo.c`` 生成 ``foo.bc`` ，然后在
链接时做 LTO（链接时优化）。整个过程中，编译器只操作内存中的 IR 对象，
bitcode 用于磁盘存储，而文本形式只在调试或手工分析时使用——就像汇编代码
之于机器码的关系。

一个完整的 .ll 文件
======================

让我们从一个完整的 ``.ll`` 文件入手，逐步拆解它的每个组成部分：

.. code-block:: llvm
   :caption: hello.ll 的完整结构

   ; ModuleID = 'hello.c'
   source_filename = "hello.c"
   target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
   target triple = "x86_64-pc-linux-gnu"

   @.str = private unnamed_addr constant [12 x i8] c"Result: %d\0A\00"

   define i32 @add(i32 %a, i32 %b) {
   entry:
     %add = add nsw i32 %a, %b
     ret i32 %add
   }

   define i32 @main() {
   entry:
     %x = alloca i32, align 4
     store i32 42, ptr %x, align 4
     %0 = load i32, ptr %x, align 4
     %1 = load i32, ptr %y, align 4
     %call = call i32 @add(i32 %0, i32 %1)
     ret i32 0
   }

   declare i32 @printf(ptr, ...)

文件由以下几部分构成：

**第 1 层 -- 目标描述**

``target datalayout`` 字符串描述了目标平台的数据布局。它包含多个用 ``-`` 分隔的
标记，如 ``e`` 表示小端序、``p64:64:64`` 表示 64 位指针的对齐方式等。
``target triple`` 的格式是 ``<arch>-<vendor>-<os>-<environment>`` 。

**第 2 层 -- 顶层实体**

一个 ``.ll`` 文件包含若干个顶层声明：全局变量（以 ``@`` 开头）、函数定义
（``define`` ）、函数声明（``declare`` ）、元数据（以 ``!`` 开头）。

**第 3 层 -- 函数体**

每个函数体由若干个**基本块** 组成。每个基本块有一个标签，包含一系列指令，
并以终止指令（如 ``ret`` 、``br`` ）结束。

标识符：@ 与 %
================

LLVM IR 中有两类标识符：

- **全局标识符**\ （``@`` ）：全局变量、函数名、全局常量，在整个 Module 中唯一
- **局部标识符**\ （``%`` ）：局部变量、基本块标签，在函数范围内唯一

两类标识符都支持**命名标识符** 和**数字标识符** 两种形式：

.. code-block:: llvm

   ; 命名标识符（可读性好）
   %result = add i32 %a, %b

   ; 数字标识符（编译器自动生成）
   %0 = add i32 %1, %2

基本类型系统
================

LLVM IR 拥有一个**显式类型系统**——每条指令的操作数都明确标注了类型。

**基本类型一览：**

.. list-table::
   :header-rows: 1

   * - 类型关键字
     - 含义
     - 示例
   * - ``void``
     - 无返回值
     - ``ret void``
   * - ``i1``
     - 1 位整数（布尔值）
     - ``%cmp = icmp eq i32 %a, %b``
   * - ``i8`` / ``i16`` / ``i32`` / ``i64``
     - 8/16/32/64 位整数
     - ``%x = add i32 %a, %b``
   * - ``iN``
     - 任意位宽整数
     - ``%x = add i17 %a, %b``
   * - ``half`` / ``float`` / ``double``
     - 16/32/64 位浮点
     - ``%f = fadd float %a, %b``
   * - ``ptr``
     - 指针（不透明，无指向类型信息）
     - ``%p = alloca i32``
   * - ``label``
     - 基本块标签
     - ``br label %target``

在 C 语言中你可以写 ``int a; float b = a;`` 让编译器隐式转换，但 LLVM IR 中
转换必须显式写出。这种设计消除了歧义并简化了优化器。

你可以在 ``llvm/include/llvm/IR/Type.h`` 中看到 LLVM 的类型系统实现。
``Type::TypeID`` 枚举定义了所有内置类型，包括 ``IntegerTyID`` 、\ ``PointerTyID`` 、
``StructTyID`` 、\ ``ArrayTyID`` 等。

注意 LLVM 15 之后，指针类型变成了**不透明指针** （opaque pointer），统一为
``ptr`` ，不再携带指向类型信息。这是一个重要的简化。

SSA 形式与 phi 节点
========================

LLVM IR 采用**静态单赋值** （SSA）形式：每个值只定义一次。

.. code-block:: llvm

   %x = add i32 %a, %b   ; 定义 %x
   %y = mul i32 %x, 2    ; 使用 %x
   %z = add i32 %x, %y   ; 使用 %x 和 %y

优化器看到 ``%y`` 时就能立即追溯它的来源是 ``%x`` 和常量 ``2`` 。
如果 ``%x`` 没有被使用，它就可以被删除。

**但 SSA 在控制流汇合时有问题：** 当两个控制流路径汇合时，同一个变量可能来自
不同的定义。LLVM 用 ``phi`` 指令来解决：

.. code-block:: llvm

   define i32 @sum(i32 %n) {
   entry:
     br label %loop

   loop:
     %i = phi i32 [ 0, %entry ], [ %next, %loop ]
     %acc = phi i32 [ 0, %entry ], [ %sum, %loop ]
     %next = add i32 %i, 1
     %sum = add i32 %acc, %i
     %done = icmp eq i32 %next, %n
     br i1 %done, label %exit, label %loop

   exit:
     ret i32 %acc
   }

``phi`` 指令的含义是："根据进入当前基本块的上一个基本块，选择对应的值"。
当控制流从 ``%entry`` 进入 ``%loop`` 时，``%i`` 取值为 ``0`` ；
当从 ``%loop`` 自身跳回时，``%i`` 取值为 ``%next`` 。

关于 ``phi`` 的源码实现，参见 ``llvm/include/llvm/IR/Instructions.h`` 中的
``PHINode`` 类。它内部维护一个 ``(Value, BasicBlock*)`` 对的列表。