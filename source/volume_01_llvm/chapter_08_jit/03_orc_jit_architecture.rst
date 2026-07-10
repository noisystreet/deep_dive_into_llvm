.. _chapter-08-03-orc-jit-architecture:

======================
ORC JIT 架构
======================

ORC JIT（Omni-Range Code JIT）是 LLVM 当前主推的 JIT 编译框架。它从 LLVM 6
开始引入，目标是解决 MCJIT 的所有局限——**分层、异步、可组合** 。

.. rst-class:: center

   如果说 MCJIT 是一个"编译器"，ORC JIT 就是一个"编译器操作系统"——
   它管理编译任务、依赖关系和资源。

.. admonition:: ORC 的名字：Omni-Range Code 的含义
   :class: note

   **Omni-Range** 意为"全范围"——ORC JIT 不假设你只 JIT 一个函数或一个模块，
   而是管理 **任意数量、任意依赖关系** 的代码单元。核心抽象：

   - **JITDylib** — 类似动态库，容纳一组符号
   - **MaterializationUnit** — 延迟编译的代码单元
   - **ExecutionSession** — 协调查找、编译、链接的总调度器

   对比 MCJIT 的"一次性编译整个模块"，ORC 支持 **懒编译**——
   函数第一次被调用时才触发编译，且已编译的函数可以跨 Session 缓存。
   LLJIT 在此基础上封装了更简洁的 API，成为今天 LLVM JIT 的事实标准。

ORC JIT 的设计哲学
======================

ORC JIT 的核心抽象包括三个层次：

.. mermaid::

   flowchart TD
       subgraph ExecutionSession
           subgraph JITDylib
               subgraph Layer 栈
                   L1[IRTransformLayer\nIR 优化]
                   L2[CompileOnDemandLayer\n懒编译]
                   L3[IRCompileLayer\nIR → 目标代码]
                   L4[ObjectLinkingLayer\n链接 + 内存加载]
               end
           end
       end

       style ExecutionSession fill:#4a9eff,color:#fff
       style JITDylib fill:#ff9800,color:#fff

1. **ExecutionSession** （执行会话）：顶层协调器，管理所有 JITDylib 和线程
2. **JITDylib** （JIT 动态库）：符号解析的作用域，相当于动态链接中的"共享对象"
3. **Layer** （层）：编译流水线中的处理步骤，可以叠加

ExecutionSession
====================

``ExecutionSession`` 是 ORC JIT 的"全局上下文"。它负责：

- 管理多个 ``JITDylib``
- 管理后台编译线程
- 提供错误处理和日志

.. code-block:: cpp

   // 创建 ExecutionSession
   ExecutionSession ES;
   // 获取"主"JITDylib（默认的符号作用域）
   auto &JD = ES.createJITDylib("main");
   // 后续的 JIT 操作都在这个 session 中进行

一个进程可以有多个 ExecutionSession，但通常只需要一个。

JITDylib
============

``JITDylib`` 是 ORC JIT 的 **符号查找作用域** 。它的工作方式类似于 Linux 中的
共享对象——每个 JITDylib 有一个符号表，其中每个符号可以被定义或未定义。

.. code-block:: cpp

   // 创建 JITDylib 并设置搜索顺序
   auto &JD = ES.createJITDylib("main");
   auto &STD = ES.createJITDylib("stdlib");

   // main 中找不到的符号去 stdlib 中找
   JD.addToSearchOrder(&STD);

当 ORC JIT 需要解析一个符号时，它会首先在定义该符号的 JITDylib 中查找，
然后按照搜索顺序在其他 JITDylib 中查找。这模拟了动态链接器的符号解析过程。

Layer（层）
================

Layer 是 ORC JIT 编译流水线中的处理单元。每个 Layer 封装一个特定功能，
多个 Layer 可以 **叠加** （stacked）形成完整的编译管道。

.. list-table:: ORC JIT 核心 Layer
   :header-rows: 1

   * - Layer
     - 输入
     - 输出
     - 功能
   * - ``IRTransformLayer``
     - ``llvm::Module``
     - ``llvm::Module``
     - 优化 IR（运行 LLVM Pass）
   * - ``IRCompileLayer``
     - ``llvm::Module``
     - ``ObjectFile``
     - 将 IR 编译为目标文件
   * - ``CompileOnDemandLayer``
     - ``llvm::Module``
     - 部分编译的 Module
     - 实现懒编译（按需编译）
   * - ``ObjectLinkingLayer``
     - ``ObjectFile``
     - 内存中的可执行代码
     - 链接 + 重定位 + 内存加载

Layer 叠加的典型方式：

.. code-block:: cpp

   // 底层：目标文件链接层
   auto ObjLayer = std::make_unique<ObjectLinkingLayer>(ES);

   // 中间层：IR → 目标文件
   auto CompileLayer = std::make_unique<IRCompileLayer>(
       *ObjLayer, CompileFunction);

   // 上层：可选 IR 变换（如优化）
   auto OptimizeLayer = std::make_unique<IRTransformLayer>(
       *CompileLayer, OptimizeFunction);

   // 顶层：懒编译
   auto CODLayer = std::make_unique<CompileOnDemandLayer>(
       *OptimizeLayer);

Materialization 过程
=========================

"物化"（Materialization）是 ORC JIT 的核心概念：从 IR 到可执行代码的整个过程。

1. **用户提交 IR** ：通过 ``JD.add(IRModule(M))`` 将 Module 添加到 JITDylib
2. **分区** （Partitioning）：CompileOnDemandLayer 将 Module 拆分为函数粒度的分区
3. **编译触发** ：当外部代码首次调用某个函数时，对应的分区才被编译
4. **编译与链接** ：IRCompileLayer 编译 IR，ObjectLinkingLayer 加载并重定位
5. **缓存** ：编译结果被缓存，同一函数不会被编译两次

.. code-block:: text

   时间轴：

   提交:  ──── Module ────→ [CODLayer: 分区]
                                    │
   首次调用 foo():                  │
           ── call foo ──→ [CODLayer: 触发 foo 的编译]
                            → [OptimizeLayer: 优化 IR]
                            → [IRCompileLayer: IR → .o]
                            → [ObjectLinkingLayer: 加载]
                            → foo() 可执行

   再次调用 foo(): 直接执行缓存的机器码

异步编译支持
================

ORC JIT 的一个关键特性是 **异步编译** 。 ``ExecutionSession`` 可以配置后台编译线程，
使编译与执行重叠：

.. code-block:: cpp

   // 创建异步编译线程池
   auto &ThreadPool = ES.createThreadPool();

   // 使用异步 dispatch
   ES.setDispatchTask(
       [&](std::unique_ptr<Task> T) {
           ThreadPool.async([T = std::move(T)]() { T->run(); });
       });

这允许多个 Module 同时被编译，提高多核利用率。

在源码中的位置
=================

.. code-block:: text

   llvm/include/llvm/ExecutionEngine/Orc/
   ├── ExecutionSession.h
   ├── JITDylib.h
   ├── Layer.h
   ├── IRCompileLayer.h
   ├── ObjectLinkingLayer.h
   ├── CompileOnDemandLayer.h
   ├── IRTransformLayer.h
   └── ...

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
