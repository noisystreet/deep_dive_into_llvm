.. _chapter-09-03-lli-and-jit-tools:

==========================
lli 与 JIT 工具
==========================

``lli`` 是 LLVM 的 JIT 编译器/解释器。它直接读取 LLVM IR（``.ll`` 或 ``.bc`` ），
在内存中编译并执行，不需要经过传统的汇编/链接流程。

.. rst-class:: center

   ``lli`` 把 LLVM IR 当作一门"可执行的编程语言"——你写 IR，它直接运行。

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

JIT 后端选择
================

``lli`` 支持多个 JIT 后端，通过 ``-jit-kind`` 选项切换：

.. code-block:: console

   # 使用 ORC JIT（默认，推荐）
   $ lli -jit-kind=orc hello.ll

   # 使用 MCJIT（旧版）
   $ lli -jit-kind=mcjit hello.ll

ORC JIT 是默认且推荐的后端。它提供了更好的性能和更多的功能特性。

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

lli 与外部符号
====================

``lli`` 需要解析 IR 中引用的外部符号（如 ``printf``、``malloc`` ）。它通过以下
方式查找符号：

1. **当前进程的符号表**：``lli`` 可以访问主程序（包括动态链接库）的符号
2. **显式加载的共享库**：通过 ``-load`` 选项加载
3. **JIT 定义的符号**：通过 IR 中的 ``declare`` 声明

.. code-block:: cpp

   // lli 内部通过 DynamicLibrary 查找符号
   // 它会扫描当前进程的所有已加载符号
   void *Sym = sys::DynamicLibrary::SearchForAddressOfSymbol("printf");

JIT 场景下的性能分析
========================

.. code-block:: console

   # 统计编译时间
   $ lli -time-compile hello.ll

   # 测量执行时间
   $ time lli hello.ll

   # 调试 JIT 内存管理
   $ lli -debug-only=section-manager hello.ll

实战：用 lli 测试 IR 代码
==============================

``lli`` 是学习和调试 LLVM IR 的神器。你可以在不经过完整编译流程的情况下，
快速验证一段 IR 的行为：

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

在源码中的位置
====================

`llvm/tools/lli/lli.cpp <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/tools/lli/lli.cpp>`__

``lli`` 的源码演示了如何基于 LLJIT 构建一个最小化的 JIT 执行器——
它比第 8 章中自定义 JIT 的示例还要简单。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
