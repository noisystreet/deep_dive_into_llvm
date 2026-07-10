.. _chapter-08-01-jit-overview:

==================
JIT 编译概述
==================

JIT（Just-In-Time）编译是一种在 **运行时** 将代码编译为机器码的技术。
与传统的 AOT（Ahead-Of-Time）编译不同，JIT 编译发生在程序执行过程中。

.. rst-class:: center

   AOT 编译是"建好再跑"，JIT 编译是"边跑边建"。

.. admonition:: 从 MCJIT 到 ORC：LLVM JIT 的两次重生
   :class: note

   LLVM 的 JIT 能力经历过两次彻底的重写：

   **第一代：MCJIT（2013）**
   MCJIT 的"MC"代表 Machine Code。它是 LLVM 第一个真正可用的 JIT 引擎，
   但仍然有很多局限：所有代码必须在 JITSession 中一次性编译（不支持
   增量编译）、内存管理粗放、不支持多线程。

   **第二代：ORC JIT（2016 - 至今）**
   ORC（On Request Compilation）由 Lang Hames（Apple）主导设计。
   它完全重新定义了 LLVM 的 JIT 架构。名字中的"On Request"说明了
   核心思想： **按需编译，延迟执行** 。

   ORC 的设计灵感来自操作系统虚拟内存的"按需分页"：
   - 不是一次加载所有页，而是在访问缺页时才加载
   - 同样，不是一次编译所有函数，而是在函数被调用时才编译

   这个设计带来了质的飞跃：
   - **增量编译** ：可以逐函数、逐模块地添加代码
   - **Lazy 编译** ：函数在首次调用时才编译，启动时间从秒级降到毫秒级
   - **多 JIT 实例** ：多个独立的 JIT 可以共存
   - **析构支持** ：JIT 代码可以安全地卸载和释放

   Lang Hames 在某次 LLVM 开发者大会的演讲里说：\ "ORC 的最终目标，
   是让 JIT 编译变成一种 **语言特性** ，而不是编译器的附属工具。"

为什么需要 JIT？
====================

JIT 编译有几个核心优势：

**1. 跨平台分发**

你可以分发 LLVM IR（或比特码），让目标平台在运行时将其 JIT 编译为本地代码。
这样一份 IR 可以在 x86、ARM、RISC-V 等任何 LLVM 支持的平台上运行。

**2. 运行时优化**

JIT 编译器可以收集程序的运行时信息（如哪些分支更常被执行、哪些类型更常出现），
然后针对实际情况做出更激进的优化（如推测去虚拟化、类型特化）。

**3. 动态代码生成**

某些应用场景需要在运行时生成代码——SQL 查询引擎（如 DuckDB）可以为每个查询
生成专门的代码路径；正则表达式引擎可以为特定模式生成优化的匹配代码。

LLVM JIT 的历史
====================

LLVM 的 JIT 基础设施经历了三个主要阶段：

.. list-table:: LLVM JIT 演进
   :header-rows: 1

   * - 阶段
     - 时间
     - 特点
     - 状态
   * - **传统 JIT**
     - LLVM 1.0 ~ 3.6
     - 基于 ``llvm::Function`` 级别的懒编译
     - 已移除
   * - **MCJIT**
     - LLVM 3.5 ~ 至今
     - 基于 MC 层的模块级编译
     - 维护模式
   * - **ORC JIT**
     - LLVM 6.0 ~ 至今
     - 分层、异步、可组合
     - 当前主力

传统 JIT 是 LLVM 最早期的 JIT 实现。它在函数级别工作：当一个函数首次被调用时，
它才被编译。但这种设计的缺点是 **线程不安全** ，而且在 LLVM IR 的演进过程中
越来越难以维护。LLVM 3.6 之后被移除，由 MCJIT 取代。

MCJIT 在模块级别工作（整个 ``llvm::Module`` 一起编译），使用 LLVM 的 MC 层
生成目标代码。它比传统 JIT 更稳定、更完整，但缺少懒编译（lazy compilation）支持。

ORC JIT（ORC 是 "One Remote Code" 或 "Omni-Range Code" 的意思）是 LLVM 当前
推荐的 JIT 框架。它从 LLVM 6 开始引入，并在此后的版本中持续改进。

JIT 的核心挑战
====================

实现一个 JIT 编译器比 AOT 编译器更复杂，因为它需要解决一些额外的问题：

**代码生成速度**

JIT 编译发生在程序运行时，所以编译速度直接影响程序性能。
AOT 编译器可以花几秒钟优化，JIT 编译器的优化必须在 **毫秒级** 完成。

**内存管理**

生成的机器码需要存放在 **可执行内存** 中（通常用 ``mmap`` 分配带有 ``PROT_EXEC``
权限的内存页）。JIT 还需要管理代码的释放和更新（当优化版本生成后替换旧版本）。

**符号解析**

JIT 编译器需要解析外部符号（如 ``printf`` 、 ``malloc`` 等）。在 AOT 编译中，
这是链接器的工作；在 JIT 编译中，JIT 引擎需要自己管理符号表。

**代码重定位**

生成的机器码包含绝对地址引用。JIT 引擎需要在运行时处理这些重定位。

**调试支持**

JIT 生成的代码也需要支持调试。LLVM 通过 ``DebugInfo`` 和 ``JITEventListener``
提供 GDB/JIT 注册接口，让调试器知道 JIT 生成的代码。

LLVM JIT 的工作方式
=======================

.. mermaid::

   flowchart LR
       A[LLVM IR / .bc] --> B[JIT 引擎]
       B --> C[TargetMachine]
       C --> D[MC 层代码生成]
       D --> E[可执行内存]
       E --> F[函数指针]
       F --> G[调用执行]

       style A fill:#4caf50,color:#fff
       style E fill:#ff9800,color:#fff

无论使用哪种 JIT 引擎，基本流程都是：

1. 接收 LLVM IR（或从源码编译得到 IR）
2. 调用 TargetMachine 的 ``addPassesToEmitFile`` 或直接使用 MC 层生成机器码
3. 将机器码复制到可执行内存页
4. 解析符号引用，处理重定位
5. 返回函数指针，供调用者执行

在后续几节中，我们将深入 MCJIT 和 ORC JIT 的实现细节。
