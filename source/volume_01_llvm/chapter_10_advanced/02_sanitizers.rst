.. _chapter-10-02-sanitizers:

==========================
Sanitizer 工具
==========================

LLVM 的 Sanitizer 工具是一组 **运行时动态分析工具** ，通过在编译时插入检测代码，
在运行时捕获各类程序错误。

.. rst-class:: center

   Sanitizer 把传统的"分段错误、随机崩溃"变成了清晰的错误报告——
   告诉你 **哪行代码、什么类型、触发了什么错误** 。

.. admonition:: Sanitizer 的"编译期插桩"哲学
   :class: note

   Sanitizer 的核心思路是 **在编译期插入检测代码** ，而非依赖外部调试器。
   ASan 在每个内存访问前插入"这片区域是否合法"的检查；
   UBSan 在每个可能溢出的运算前插入边界检查。

   代价是性能：ASan 通常让程序慢 2x、内存多 3x。但 Google 的生产经验表明，
   这点开销远低于"线上崩溃 + 人工排查"的成本——Chrome、Android 系统服务
   都在 CI 中默认开启 ASan。LLVM 的插桩 Pass 位于
   ``llvm/lib/Transforms/Instrumentation/`` ，与优化 Pass 共享同一套 IR 基础设施。

AddressSanitizer（ASan）
=============================

ASan 捕获 **内存错误** ：缓冲区溢出、释放后使用、双重释放、栈/全局缓冲区溢出。

.. code-block:: console

   $ clang -fsanitize=address -g test.c -o test
   $ ./test
   ======================================================
   ERROR: AddressSanitizer: heap-buffer-overflow
       WRITE of size 4 at 0x6020000000fc thread T0
       #0 0x4f5b8c in main /tmp/test.c:5:9
       0x6020000000fc is located 0 bytes after 4-byte region
       allocated by thread T0 here:
       #0 0x4f3b8c in malloc /tmp/test.c:4:13
       #1 0x4f5b7c in main /tmp/test.c:4:13
   ======================================================

ASan 的工作原理：

1. 在每次 **堆内存分配** 时，在分配区域周围添加"红区"（redzone）
2. 在每次 **内存访问** （load/store）时，检查访问地址是否在有效区域内
3. 如果访问到了红区，立即报告错误

ASan 的编译插桩会：

- 将所有 ``malloc``/``free`` 替换为 ASan 的包装版本
- 在所有 ``load``/``store`` 指令前插入检查代码
- 在栈变量周围添加红区

ASan 的性能开销约为 **2x 运行时间** 和 **3x 内存使用** 。

UndefinedBehaviorSanitizer（UBSan）
=========================================

UBSan 捕获 **未定义行为** ：整数溢出、空指针解引用、除零、越界移位等。

.. code-block:: console

   $ clang -fsanitize=undefined test.c -o test
   $ ./test
   test.c:3:13: runtime error: signed integer overflow:
       2147483647 + 1 cannot be represented in type 'int'

可检测的未定义行为类型：

.. code-block:: console

   $ clang -fsanitize=undefined  # 启用所有未定义行为检测

   # 也可以单独启用
   $ clang -fsanitize=null           # 空指针解引用
   $ clang -fsanitize=shift          # 越界移位
   $ clang -fsanitize=integer        # 整数溢出
   $ clang -fsanitize=float-divide-by-zero  # 浮点除零
   $ clang -fsanitize=return         # 无返回值函数

UBSan 的性能开销很小（通常 <5%），适合在测试和开发阶段常开。

在源码中的位置：`llvm/lib/Transforms/Instrumentation/ <file:///workspace/llvm-project/llvm/lib/Transforms/Instrumentation/>`__

ThreadSanitizer（TSan）
==============================

TSan 检测 **数据竞争**——多个线程同时访问同一内存位置，且至少有一个是写操作。

.. code-block:: console

   $ clang -fsanitize=thread -g test.c -o test -lpthread
   $ ./test
   ==================
   WARNING: ThreadSanitizer: data race (pid=1234)
     Write of size 4 at 0x7f0000000008 by thread T1:
       #0 inc /tmp/test.c:5:3

     Previous read of size 4 at 0x7f0000000008 by main thread:
       #0 main /tmp/test.c:15:7

     Location is global 'counter' at 0x7f0000000008
   ==================

TSan 的性能开销约为 **5x~10x** 运行时间和 **5x~10x** 内存使用。

MemorySanitizer（MSan）
==============================

MSan 检测 **未初始化内存的读取** 。

.. code-block:: console

   $ clang -fsanitize=memory -g test.c -o test
   $ ./test
   WARNING: MemorySanitizer: use-of-uninitialized-value
       #0 main /tmp/test.c:4:5

MSan 的工作原理：为程序中的每一位内存维护一个"影子位"（shadow bit）。
当内存被分配时，影子位标记为"未初始化"；当内存被写入时，影子位标记为"已初始化"。
读取未初始化的内存时，MSan 报告错误。

MSan 需要 **链接所有库时都开启 MSan 编译** ，否则会有误报。

LeakSanitizer（LSan）
===========================

LSan 检测 **内存泄漏**——分配但没有释放的内存。

.. code-block:: console

   $ clang -fsanitize=leak -g test.c -o test
   $ ./test
   =================================================================
   1 bytes leaked in 1 allocations.
   LeakSanitizer: detected memory leaks
   Direct leak of 100 byte(s) in 1 object(s) allocated from:
       #0 malloc /tmp/test.c:3:9

LSan 通常在 ASan 中默认启用（ ``-fsanitize=address`` 自动包含 LSAN）。

Sanitizer 的编译插桩机制
===============================

Sanitizer 在 LLVM 的 **中端** （Mid-end）实现——它们在 IR 层面插入检测代码，
然后才交给后端生成机器码。

.. code-block:: text

   源码 → Clang AST → LLVM IR → Sanitizer Pass → 优化 → 代码生成
                                       │
                                   插入检测代码
                                   （红区、影子内存、检查函数调用）

Sanitizer Pass 的注册位置：

.. code-block:: cpp

   // llvm/lib/Transforms/Instrumentation/AddressSanitizer.cpp
   PreservedAnalyses AddressSanitizerPass::run(
       Function &F, FunctionAnalysisManager &AM) {
       // 遍历所有 load/store 指令
       // 在它们之前插入检查代码
   }

在 CMake 中使用 Sanitizer
================================

.. code-block:: cmake

   # 在项目中开启 ASan
   set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fsanitize=address -g")
   set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fsanitize=address")

   # 或通过 CMake 的内置支持
   set(CMAKE_C_FLAGS_SANITIZE "address" CACHE STRING "Sanitizer type")

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
