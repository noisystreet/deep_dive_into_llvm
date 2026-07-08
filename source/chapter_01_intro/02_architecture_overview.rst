.. _chapter-01-02-architecture-overview:

==========================
LLVM 架构概览
==========================

上一节我们看到了 LLVM 的庞大生态。但这些子项目是如何组织在一起的？编译器编译代码
的完整流程是什么样的？这一节我们从架构层面来拆解 LLVM 的设计。

从问题出发：传统编译器的痛点
================================

在 LLVM 诞生之前，GCC 是开源世界的主流编译器。GCC 的架构是**前端-中端-后端**
三者耦合在一起的：每个前端（C、C++、Fortran、Ada、Java 等）有自己独特的中间表示，
没有统一的 IR。这意味着：

- 想为一种新语言写前端，你不仅需要写词法/语法分析，还需要写一个完整的优化器和后端
- 想新增一种优化算法，你需要在每个中间表示层上都实现一遍
- 想迁移到新硬件架构，你需要为每个前端提供一套独立的代码生成器

这显然不可持续。LLVM 的核心理念就是解决这个问题。

三阶段架构
================

LLVM 将编译过程划分为三个独立的阶段：

.. rst-class:: center

   ``Source Code → Frontend → [LLVM IR] → Optimizer → [LLVM IR] → Backend → Machine Code``

1. **前端（Frontend）** — 将源代码翻译为 LLVM IR
2. **优化器（Optimizer）** — 对 LLVM IR 进行与语言和目标无关的优化
3. **后端（Backend）** — 将 LLVM IR 翻译为目标机器码

这三者通过 **LLVM IR** 这一唯一的中间表示解耦。前端只需生成合法的 LLVM IR，
后端只需消费 LLVM IR，优化器则在 IR 上做变换。任何一端的变化都不会影响另一端。

.. mermaid::

   flowchart LR
       C[C/C++ Source] --> Clang
       Rust[Rust Source] --> Rustc
       Fortran[Fortran Source] --> Flang

       Clang --> IR1[LLVM IR]
       Rustc --> IR1
       Flang --> IR1

       IR1 --> Opt[Optimizer]
       Opt --> IR2[Optimized LLVM IR]
       IR2 --> X86[X86 Backend]
       IR2 --> ARM[ARM Backend]
       IR2 --> RISCV[RISC-V Backend]
       IR2 --> WASM[WebAssembly Backend]

       X86 --> X86Asm[x86 Assembly]
       ARM --> ARMAsm[ARM Assembly]
       RISCV --> RISCVAsm[RISC-V Assembly]
       WASM --> WASMAsm[WebAssembly]

       style IR1 fill:#ff9900,stroke:#333,color:#fff
       style IR2 fill:#ff9900,stroke:#333,color:#fff

上图展示了 LLVM 架构的核心优势：N 种语言前端 + M 个目标后端 = N × M 种语言-目标组合，
但你只需要实现 N + M 个组件，因为 IR 是统一的"翻译站"。这就叫 **"一次编写 IR，处处代码生成"**。

LLVM IR — 统一中间表示
==============================

LLVM IR 是整个架构的**基石**。它是一种**静态单赋值（SSA, Static Single Assignment）**
形式的低级中间表示，同时具备三个形态：

**三种形态的 IR：**

.. list-table::
   :header-rows: 1

   * - 形态
     - 格式
     - 用途
     - 示例
   * - 文本形态（.ll）
     - 可读的汇编风格文本
     - 调试、教学、手工分析
     - ``%result = add i32 %a, %b``
   * - 二进制形态（.bc）
     - 紧凑的 bitcode 格式
     - 存储、传输、链接
     - 使用 ``llvm-dis`` 反汇编为 .ll
   * - 内存形态（C++ 对象）
     - ``llvm::Module``、\ ``llvm::Function`` 等
     - 编译器内部操作
     - Pass 通过 C++ API 操作 IR

为什么三种形态？因为 LLVM 的设计哲学是"不丢失信息"——无论你是在手工调试（文本）、
做链接时优化（bitcode），还是在代码中操控 IR（API），同一个程序在不同形态间转换
是完全无损的。

核心数据结构：

- ``llvm::Module`` （`:file:///workspace/llvm-project/llvm/include/llvm/IR/Module.h`）— 
  一个编译单元（通常对应一个源文件）的顶层容器，包含函数、全局变量、元数据等
- ``llvm::Function`` — 表示一个函数，包含多个 BasicBlock
- ``llvm::BasicBlock`` — 基本块，包含一系列指令序列，以控制流终止指令结束
- ``llvm::Instruction`` — 单条指令的操作码和操作数

举个具体的例子。一个 C 函数:

.. code-block:: c

   int add(int a, int b) {
       return a + b;
   }

对应的 LLVM IR 是：

.. code-block:: llvm

   define i32 @add(i32 %a, i32 %b) {
   entry:
       %result = add i32 %a, %b
       ret i32 %result
   }

``i32`` 是 32 位整数类型，``%a``、``%b`` 是 SSA 值（每个值只被赋值一次），
``add`` 指令的两个操作数分别是 ``%a`` 和 ``%b``。看到没有——IR 中没有任何
与 C 语言相关的信息（没有类型名、没有 C 的关键字），只有最底层的整数运算。
这就是"语言无关"的含义：同样的 IR 也可以由 Rust 编译器生成。

关于 IR 的详细语法和语义，我们在第 2 章会专门展开。

编译流水线
==============

现在我们把三阶段架构展开，看看从源代码到机器码的完整流水线。

以 Clang 编译 ``hello.c`` 为例：

.. mermaid::

   flowchart LR
       S[hello.c] --> Lex[词法分析]
       Lex --> Parse[语法分析]
       Parse --> Sema[语义分析]
       Sema --> AST[AST]
       AST --> CodeGen[CodeGen]
       CodeGen --> IR[LLVM IR]

       IR --> Opt[优化 Pass 链]
       Opt --> OptIR[优化后的 IR]

       OptIR --> ISel[指令选择]
       ISel --> DAG[SelectionDAG]
       DAG --> RegAlloc[寄存器分配]
       RegAlloc --> MC[MC 层]
       MC --> Asm[汇编/目标文件]

       style AST fill:#4a90d9,stroke:#333,color:#fff
       style IR fill:#ff9900,stroke:#333,color:#fff
       style OptIR fill:#ff9900,stroke:#333,color:#fff

每个阶段的职责：

**前端阶段（Clang）：**

1. **词法分析** （Lexer）：将字符流拆解为 token（关键字、标识符、操作符等）
2. **语法分析** （Parser）：根据 C/C++ 语法规则将 token 组合成 AST（抽象语法树）
3. **语义分析** （Sema）：检查类型是否正确、变量是否已声明等语义约束
4. **CodeGen**\ （代码生成）：将 AST 翻译为 LLVM IR

Clang 的入口在 ``clang/tools/driver/driver.cpp``，
核心 AST 生成逻辑在 ``clang/lib/Parse/`` 和 ``clang/lib/Sema/`` 中。

**优化阶段（opt 工具）：**

优化器以 LLVM IR 为输入，应用一系列 **Pass**\ （优化通道），输出优化后的 IR。
Pass 分为两类：

- **分析 Pass**\ （Analysis Pass）：分析 IR 但不修改它，生成供其他 Pass 使用的信息
  （如 ``DominatorTreeAnalysis`` 计算支配树）
- **变换 Pass**\ （Transform Pass）：修改 IR 来优化它，如函数内联（``InlinerPass``）、
  常量传播（``SCCPPass``）、循环向量化（``LoopVectorizePass``）

优化器的入口是 ``opt`` 工具（源码在 ``llvm/tools/opt/``），我们会在第 5 章深入
讨论各优化算法。

**后端阶段（llc 工具）：**

后端将优化后的 IR 翻译为目标机器码。后端内部又分为多个子阶段：

1. **指令选择**\ （Instruction Selection）：将 LLVM IR 指令映射为目标机器的指令，
   使用 SelectionDAG（有向无环图）表示
2. **寄存器分配**\ （Register Allocation）：将无限的虚拟寄存器映射到有限的物理寄存器
3. **指令调度**\ （Instruction Scheduling）：重排指令顺序以利用 CPU 流水线
4. **MC 层**\ （Machine Code Layer）：将机器指令编码为二进制或汇编文本

后端的入口是 ``llc`` 工具（源码在 ``llvm/tools/llc/llc.cpp``）。
我们在第 7 章会详细分析后端流程。

两个编译模式
================

LLVM 支持两种运行模式：

**1. 静态编译（离线编译）**

这是最常见的模式——Clang 一次性将源文件编译为可执行文件：

.. code-block:: bash

   clang hello.c -o hello
   ./hello

Clang 内部完成了"前端 → 优化器 → 后端"的全流程，最终生成机器码并链接为
可执行文件。

**2. JIT 编译（即时编译）**

LLVM 可以将 IR "即时"编译为机器码并在当前进程中执行。这意味着你可以编写
一个在运行时生成代码的程序，然后立即执行它——这正是 Julia、Rustc 的
增量编译、以及数据库查询 JIT 编译等场景的技术基础：

.. code-block:: bash

   lli hello.ll   # 直接运行 LLVM IR

JIT 编译的核心 API 在 ``llvm/lib/ExecutionEngine/`` 和 ``llvm/tools/lli/`` 中。
我们在第 8 章会系统讲解 JIT。

源码目录结构
================

理解了架构后，再看 ``llvm-project/llvm/`` 的目录结构就清晰了：

.. list-table::
   :header-rows: 1

   * - 目录
     - 内容
     - 对应架构层
   * - ``include/llvm/IR/``
     - LLVM IR 核心类型定义（Module, Function, Instruction 等）
     - IR 层
   * - ``include/llvm/Analysis/``
     - 分析 Pass 的接口
     - 优化器
   * - ``include/llvm/Transforms/``
     - 变换 Pass 的接口
     - 优化器
   * - ``include/llvm/CodeGen/``
     - 代码生成相关的接口
     - 后端
   * - ``include/llvm/Target/``
     - 目标描述抽象（TargetMachine, TargetRegisterInfo 等）
     - 后端
   * - ``include/llvm/MC/``
     - MC 层接口（汇编器、反汇编器、对象文件）
     - 后端
   * - ``lib/IR/``
     - IR 核心实现（Module.cpp, Function.cpp 等）
     - IR 层
   * - ``lib/Transforms/``
     - 各 Pass 的实现
     - 优化器
   * - ``lib/CodeGen/``
     - 代码生成器实现（指令选择、寄存器分配等）
     - 后端
   * - ``lib/Target/<ARCH>/``
     - 各后端的 Target 描述（如 ``lib/Target/X86/``）
     - 后端
   * - ``tools/``
     - 命令行工具（opt, llc, lli, llvm-dis 等）
     - 工具层

这形成了从 "IR 核心"到"后端细节"的层次递进。我们这本书也将沿着这个层次展开：
第 2 章讲 IR，第 3-4 章讲前端和 Pass 框架，第 5 章讲优化，第 6-7 章讲后端，
第 8 章讲 JIT，第 9 章讲工具链。

.. raw:: html

   <hr>
   <p><em>生成日期: 2026-07-08 &nbsp;&nbsp; 项目: 浅入深出 LLVM</em></p>