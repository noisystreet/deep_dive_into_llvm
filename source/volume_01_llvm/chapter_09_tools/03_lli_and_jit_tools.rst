.. _chapter-09-03-lli-and-jit-tools:

==========================
lli 与 JIT 工具
==========================

``lli`` 是 LLVM 的 JIT 编译器/解释器。它直接读取 LLVM IR（ ``.ll`` 或 ``.bc`` ），
在内存中编译并执行，不需要经过传统的汇编/链接流程。

.. rst-class:: center

   ``lli`` 把 LLVM IR 当作一门"可执行的编程语言"——你写 IR，它直接运行。

为什么需要 JIT 执行？
============================

传统的编译流程是 **AOT（Ahead-of-Time）**——编译时全部完成，运行时只执行。
JIT 的流程是 **运行时编译**——代码在需要执行时才被编译成机器码。

JIT 的优势在于：

- **REPL 式开发**：写一段 IR，立即看到执行结果，不需要 clang → llc → as → ld
- **优化反馈**：JIT 可以根据运行时 profile 信息动态调整优化策略
- **代码生成测试**：快速验证 IR 变换的正确性，不需要走完整编译链

``lli`` 是体验 LLVM JIT 能力的最简单方式——不需要写 C++ 代码，不需要
链接 LLVM 库，一条命令就能跑起来。

基本用法
============

.. code-block:: console

   # 直接执行 LLVM IR
   $ lli hello.ll
   Hello, LLVM!

   # 执行比特码
   $ lli hello.bc

   # 将 IR 保存为文本，用 lli 运行
   $ cat hello.ll
   declare i32 @printf(i8*, ...)
   @fmt = constant [13 x i8] c"Hello, LLVM!\0A\00"
   define i32 @main() {
       call i32 @printf(i8* getelementptr inbounds ([13 x i8], [13 x i8]* @fmt, i32 0, i32 0))
       ret i32 0
   }
   $ lli hello.ll
   Hello, LLVM!

注意上面的 IR 调用了 ``printf``——这是一个外部函数，``lli`` 通过
**动态符号查找** 在运行时解析了这个符号。这意味着 ``lli`` 可以调用
任意 C 标准库函数，甚至加载的共享库中的函数。

JIT 后端选择：从 MCJIT 到 ORC 的演进
============================================

``lli`` 支持两个 JIT 后端，通过 ``-jit-kind`` 切换：

.. code-block:: console

   # 使用 ORC JIT（默认，推荐）
   $ lli -jit-kind=orc hello.ll

   # 使用 MCJIT（旧版）
   $ lli -jit-kind=mcjit hello.ll

.. admonition:: 为什么从 MCJIT 迁移到 ORC？
   :class: note

   MCJIT（Machine Code JIT）是 LLVM 的第一代 JIT 引擎，2013 年引入。
   它的设计很简单：每次编译一个 Module，生成机器码然后执行。但有几个
   根本性问题：

   - **单线程**：所有编译在同一个线程中完成，无法利用多核
   - **全量编译**：每次编译整个 Module，不支持增量添加函数
   - **编译和执行耦合**：编译过程中不能插入自定义逻辑（如 profile 收集）

   ORC（Optimized Remote Compilation）JIT 是 2017 年重新设计的第二代
   框架，解决了这些问题。它的核心是 **分层编译**：你可以先快速编译
   一个函数（``-O0``），如果它被频繁调用，再重新编译为优化版本（``-O2``）。
   这类似于 Java JVM 的分层编译（C1/C2 编译器）。

   在源码中的位置：`llvm/include/llvm/ExecutionEngine/Orc/LLJIT.h <file:///workspace/llvm-project/llvm/include/llvm/ExecutionEngine/Orc/LLJIT.h>`__

调试选项
============

.. code-block:: console

   # 查看 JIT 编译过程
   $ lli -debug-only=orc hello.ll

   # 打印生成的机器码
   $ lli -debug-only=object-linking-layer hello.ll

   # 指定优化等级
   $ lli -O0 hello.ll   # 无优化（快速编译）
   $ lli -O2 hello.ll   # 优化执行速度

   # 强制链接外部库
   $ lli -load=libmylib.so hello.ll

``-O0`` 和 ``-O2`` 的差异在 JIT 场景下尤为明显：
- ``-O0``：编译极快，但生成的代码可能比原生慢 10 倍
- ``-O2``：编译慢一些，但运行速度快

ORC 的分层编译正是为了调和这个矛盾——先用 ``-O0`` 快速启动，然后
在后台线程用 ``-O2`` 重新编译热点函数。

lli 与外部符号
====================

``lli`` 需要解析 IR 中引用的外部符号（如 ``printf`` 、 ``malloc`` ）。它通过以下
方式查找符号：

.. code-block:: cpp

   // lli 内部通过 DynamicLibrary 查找符号
   // 它会扫描当前进程的所有已加载符号
   void *Sym = sys::DynamicLibrary::SearchForAddressOfSymbol("printf");

查找顺序是：

1. **当前进程的符号表** ：``lli`` 可以访问主程序（包括动态链接库）的符号
2. **显式加载的共享库** ：通过 ``-load`` 选项加载
3. **JIT 定义的符号** ：通过 IR 中的 ``declare`` 声明

这个机制意味着 **``lli`` 可以调用任何 C 函数**——不只是 IR 中定义的函数。
这让 ``lli`` 成为一个强大的"IR 沙箱"：你可以用 C 写性能敏感的底层函数，
用 IR 写业务逻辑，然后用 ``lli`` 把它们粘合在一起。

JIT 场景下的性能分析
========================

.. code-block:: console

   # 统计编译时间
   $ lli -time-compile hello.ll

   # 测量执行时间
   $ time lli hello.ll

   # 调试 JIT 内存管理
   $ lli -debug-only=section-manager hello.ll

``-time-compile`` 让你看到 JIT 编译本身的耗时，这在性能敏感的 JIT
场景中很关键——如果编译时间太长，可能抵消 JIT 带来的运行时加速。

实战：用 lli 做 IR 的快速原型验证
============================================

``lli`` 是学习和调试 LLVM IR 的神器。你可以在不经过完整编译流程的情况下，
快速验证一段 IR 的行为——这就像用 Python 解释器测试一段代码：

.. code-block:: console

   $ cat test.ll
   define i32 @main() {
       %x = add i32 40, 2
       %y = mul i32 %x, 2
       %z = sub i32 %y, 84
       ret i32 %z
   }
   $ lli test.ll; echo $?
   0    ; 返回值是 0

   $ cat fib.ll
   define i32 @fib(i32 %n) {
       %c = icmp ult i32 %n, 2
       br i1 %c, label %base, label %recurse
   base:
       ret i32 1
   recurse:
       %n1 = sub i32 %n, 1
       %r1 = call i32 @fib(i32 %n1)
       %n2 = sub i32 %n, 2
       %r2 = call i32 @fib(i32 %n2)
       %r = add i32 %r1, %r2
       ret i32 %r
   }
   define i32 @main() {
       %r = call i32 @fib(i32 10)
       ret i32 %r
   }
   $ lli fib.ll; echo $?
   89   ; Fibonacci(10) = 89

.. admonition:: 为什么用 ``lli`` 而不是 ``clang`` 或 ``llc`` 测试 IR？
   :class: tip

   用 ``clang -O2`` 编译一段 C 代码并运行，你看到的是"C 代码的执行结果"。
   用 ``lli`` 直接运行一段 IR，你看到的是 **"IR 本身的执行结果"** 。

   区别在于：前者经过了前端的 AST 解析、IR 生成、优化等层层变换，
   你无法确定哪个环节影响了结果。后者跳过了前端，直接从 IR 开始，
   让你可以精确地测试 IR 级别的变换是否正确。

   这对编译器的开发者非常有价值——当你写了一个新的 Pass 时，可以先用
   ``lli`` 运行优化前后的 IR 来验证 Pass 的行为是否符合预期。

在源码中的位置
====================

`llvm/tools/lli/lli.cpp <file:///workspace/llvm-project/llvm/tools/lli/lli.cpp>`__

``lli`` 的源码演示了如何基于 LLJIT 构建一个最小化的 JIT 执行器——
它比第 8 章中自定义 JIT 的示例还要简单。如果你想理解 JIT 的工作原理，
``lli`` 的源码是一个很好的起点。