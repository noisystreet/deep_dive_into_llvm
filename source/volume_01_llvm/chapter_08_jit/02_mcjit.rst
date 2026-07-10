.. _chapter-08-02-mcjit:

==============
MCJIT
==============

MCJIT（Machine Code JIT）是 LLVM 的第一代生产级 JIT 引擎。它将 LLVM IR
编译为机器码，但与传统 JIT 不同：它**不以函数为单位编译，而是以 Module 为单位** 。

.. rst-class:: center

   MCJIT 的核心思想：把 AOT 编译器的后端直接嵌入到运行时。

MCJIT 的架构
================

MCJIT 的架构相对简单——它将 LLVM 后端的代码生成链路直接暴露给运行时：

.. mermaid::

   flowchart LR
       A[LLVM Module] --> B[TargetMachine]
       B --> C[MCCodeEmitter]
       C --> D[可执行内存]
       D --> E[函数指针]

       style A fill:#4caf50,color:#fff
       style E fill:#ff9800,color:#fff

核心类是 ``llvm::MCJIT`` ，继承自 ``llvm::ExecutionEngine`` 。

使用 MCJIT
=================

下面是一个使用 MCJIT 执行 LLVM IR 的最小示例：

.. code-block:: cpp

   #include "llvm/ExecutionEngine/MCJIT.h"
   #include "llvm/IR/Module.h"
   #include "llvm/IR/LLVMContext.h"
   #include "llvm/IR/IRBuilder.h"
   #include "llvm/Support/TargetSelect.h"

   int main() {
       // 初始化目标架构
       InitializeAllTargetInfos();
       InitializeAllTargetMCs();
       InitializeAllAsmPrinters();
       InitializeAllAsmParsers();

       // 创建 LLVM Module
       LLVMContext Context;
       auto M = std::make_unique<Module>("jit_module", Context);

       // ... 在 Module 中构建 IR ...

       // 创建 MCJIT 引擎
       std::string Error;
       auto JIT = std::unique_ptr<ExecutionEngine>(
           EngineBuilder(std::move(M))
               .setEngineKind(EngineKind::JIT)
               .setErrorStr(&Error)
               .create());

       if (!JIT) {
           errs() << "Failed to create JIT: " << Error << "\n";
           return 1;
       }

       // 获取函数指针并调用
       auto *Func = JIT->findFunctionNamed("add");
       int (*Add)(int, int) =
           (int (*)(int, int))JIT->getPointerToFunction(Func);
       int Result = Add(1, 2);  // 调用 JIT 编译的函数
       outs() << "Result: " << Result << "\n";

       return 0;
   }

编译这个示例：

.. code-block:: console

   $ clang++ -std=c++17 jit_example.cpp \
       `llvm-config --cxxflags --ldflags --libs core mcjit native` \
       -o jit_example

MCJIT 的工作流程
====================

1. **接收 Module** ：调用 ``EngineBuilder::create()`` 时，MCJIT 拿到完整的 ``llvm::Module``
2. **创建 TargetMachine** ：根据目标三元组创建对应的 TargetMachine
3. **代码生成** ：调用 TargetMachine 的 ``addPassesToEmitFile`` 生成目标代码（.o 文件的内存版本）
4. **加载到内存** ：使用 ``RuntimeDyld`` 加载生成的机器码，处理重定位
5. **返回函数指针** ：通过 ``getPointerToFunction`` 返回函数入口地址

整个过程是**同步**的——当你调用 ``getPointerToFunction`` 时，MCJIT 才执行编译。

getPointerToFunction 与模块所有权
===================================

有两个重要的 API：

.. code-block:: cpp

   // 1. 经典的：传入 Function 指针，返回机器码地址
   void *getPointerToFunction(Function *F);

   // 2. 通用的：获取全局变量或函数的地址
   void *getPointerToGlobal(GlobalValue *GV);

注意：**MCJIT 接管了 Module 的所有权** 。一旦传给 MCJIT，
调用者不应该再修改原 Module。如果需要更新代码，必须创建一个新的 Module。

MCJIT 的优缺点
====================

**优点：**

- 简单可靠，API 直接
- 与 LLVM 后端紧密集成，支持所有 LLVM 支持的架构
- 支持异常处理（通过 ``MCJIT::RegisterJITEventListener`` ）

**缺点：**

- **不支持懒编译** ：整个 Module 一起编译，即使你只调用了一个函数
- **模块级粒度** ：无法对单个函数进行独立的编译和更新
- **线程安全有限** ：编译和执行的并发控制较粗糙
- **无法卸载代码** ：一旦编译，代码常驻内存直到 JIT 引擎销毁
- **开发停滞** ：LLVM 社区已停止在 MCJIT 上添加新功能

MCJIT 的现状
================

MCJIT 在 LLVM 14+ 中已经被标记为**弃用** 。新的开发工作全部集中在 ORC JIT 上。
但 MCJIT 仍然是理解 LLVM JIT 工作原理的绝佳起点——它的设计简单、代码量小，
适合作为学习 JIT 的教材。

在源码中的位置：`llvm/lib/ExecutionEngine/MCJIT/ <file:///workspace/llvm-project/llvm/lib/ExecutionEngine/MCJIT/>`__

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
