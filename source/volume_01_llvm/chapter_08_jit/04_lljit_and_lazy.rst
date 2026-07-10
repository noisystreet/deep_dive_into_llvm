.. _chapter-08-04-lljit-and-lazy:

==========================
LLJIT 与 Lazy Compilation
==========================

LLJIT（Low-Level JIT）是 ORC JIT 提供的一个 **开箱即用的高级 API** 。
它封装了 ORC JIT 的底层 Layer 栈，让你用最少的代码就能运行 JIT 编译。

.. rst-class:: center

   如果用 ORC JIT 是"搭积木"，LLJIT 就是一块"预制板"——它帮你搭好了
   最常见的 Layer 栈，你只需要填充 IR。

LLJIT 的创建
==================

LLJIT 的创建非常简单：

.. code-block:: cpp

   #include "llvm/ExecutionEngine/Orc/LLJIT.h"
   #include "llvm/Support/TargetSelect.h"

   int main() {
       // 初始化目标架构
       InitializeAllTargetInfos();
       InitializeAllTargetMCs();
       InitializeAllAsmPrinters();

       // 创建 LLJIT 实例
       auto JIT = orc::LLJITBuilder().create();
       if (!JIT) {
           errs() << "Failed to create LLJIT: "
                  << toString(JIT.takeError()) << "\n";
           return 1;
       }

       // 现在可以使用 JIT 了
       auto &ES = (*JIT)->getExecutionSession();
       // ...
   }

``LLJITBuilder`` 提供了多个配置选项：

.. code-block:: cpp

   auto JIT = orc::LLJITBuilder()
       .setJITTargetMachineBuilder(      // 指定目标架构
           JTMB->getDefaultTargetTriple())
       .setNumCompileThreads(4)          // 后台编译线程数
       .setCompileFunctionCreator(       // 自定义编译函数
           [](...) { ... })
       .create();

使用 LLJIT 编译和执行 IR
============================

.. code-block:: cpp

   // 1. 创建一个 Module
   auto M = std::make_unique<Module>("test", Context);
   // ... 在 Module 中添加函数 ...

   // 2. 将 Module 添加到 JIT
   if (auto Err = JIT->addIRModule(std::move(M))) {
       errs() << toString(std::move(Err)) << "\n";
       return 1;
   }

   // 3. 查找并调用函数
   auto AddSym = JIT->lookup("add");
   if (!AddSym) {
       errs() << toString(AddSym.takeError()) << "\n";
       return 1;
   }

   // AddSym 是一个 JITEvaluatedSymbol，包含函数地址
   auto *Add = (int (*)(int, int))AddSym->getAddress();
   int Result = Add(1, 2);

注意 ``lookup`` 返回的是 ``JITEvaluatedSymbol`` ，它包含了符号的地址和标志位。

JITDylib 管理
=================

LLJIT 默认创建一个名为 "main" 的 JITDylib。你也可以创建更多的 JITDylib 来实现
符号隔离：

.. code-block:: cpp

   // 创建额外的 JITDylib
   auto &MathJD = JIT->createJITDylib("math");
   auto &UtilJD = JIT->createJITDylib("util");

   // 设置搜索顺序
   JIT->getMainJITDylib().addToSearchOrder(&UtilJD);
   UtilJD.addToSearchOrder(&MathJD);

   // 将不同模块加载到不同的 JITDylib
   JIT->addIRModule(std::move(ModuleA), &MathJD);
   JIT->addIRModule(std::move(ModuleB), &UtilJD);

Lazy Compilation（懒编译）
===============================

**懒编译** 是指：函数只在首次被调用时才编译，而不是在 Module 被提交时立即编译。
ORC JIT 通过 ``CompileOnDemandLayer`` 实现懒编译。

使用 LLJIT 启用懒编译：

.. code-block:: cpp

   // LLJIT 默认启用懒编译
   // 通过 CompileOnDemandLayer 自动包装

   // 当你提交 Module 时，函数的编译被推迟到首次调用
   auto M = std::make_unique<Module>("lazy_module", Context);
   // ... 添加了很多函数 ...

   JIT->addIRModule(std::move(M));
   // 此时还没有任何编译发生

   // 只有当你 lookup 并调用某个函数时，它才被编译
   auto Sym = JIT->lookup("rarely_used");
   // 上面的 lookup 触发了 "rarely_used" 的编译

懒编译的实现原理是：当 Module 被提交时， ``CompileOnDemandLayer`` 分析 Module
的函数调用图，将每个函数包装为一个"桩"（stub）。当 stub 被调用时，它触发
对应函数的实际编译。

.. code-block:: text

   提交 Module 后（懒编译模式）：
   ┌─────────────────────────────────┐
   │ Module                          │
   │  foo(): [stub → 未编译]          │
   │  bar(): [stub → 未编译]          │
   │  baz(): [stub → 未编译]          │
   └─────────────────────────────────┘

   调用 foo() 后：
   ┌─────────────────────────────────┐
   │ Module                          │
   │  foo(): [已编译 ← 可执行]        │
   │  bar(): [stub → 未编译]          │
   │  baz(): [stub → 未编译]          │
   └─────────────────────────────────┘

LLJIT 内置的 Layer 栈
=========================

LLJIT 内部构建的 Layer 栈是：

.. code-block:: text

   CompileOnDemandLayer（懒编译）
         ↓
   IRTransformLayer（优化）
         ↓
   IRCompileLayer（编译）
         ↓
   ObjectLinkingLayer（加载 + 重定位）

这个栈提供了平衡的默认行为： **懒编译 → 优化 → 编译 → 链接** 。

惰性 vs 即时编译策略
========================

.. list-table:: 编译策略对比
   :header-rows: 1

   * - 策略
     - 说明
     - 适用场景
   * - **即时编译** （Eager）
     - Module 提交时立即编译所有函数
     - 小模块，频繁调用的热点代码
   * - **懒编译** （Lazy）
     - 函数首次调用时才编译
     - 大模块，有很多不常用路径
   * - **预编译** （Pre-compile）
     - 在启动时提前编译
     - 已知所有代码都会被调用

LLJIT 默认使用懒编译模式。如果要切换到即时编译，可以：

.. code-block:: cpp

   // 创建 LLJIT 时不使用 CompileOnDemandLayer
   // 直接通过 setCompileFunctionCreator 控制

在源码中的位置：`llvm/include/llvm/ExecutionEngine/Orc/LLJIT.h <file:///workspace/llvm-project/llvm/include/llvm/ExecutionEngine/Orc/LLJIT.h>`__
