.. _chapter-01-01-what-is-llvm:

==========================
什么是 LLVM？
==========================

如果你写过 C 或 C++ 代码，多半用过 Clang 来编译它。但 Clang 只是 LLVM 生态的冰山一角。
LLVM 自身是一个 **编译器基础设施**——它不是某个单一的语言编译器，而是一套用于构建编译器
的模块化工具链和库。

.. raw:: html

   <style>
   .center { text-align: center; }
   </style>

.. rst-class:: center

   从一种语言到另一种语言——LLVM 的核心理念是 **语言无关的中间表示（IR）** 。

LLVM 项目的历史与演进
========================

LLVM 始于 **2000 年** ，是伊利诺伊大学厄巴纳-香槟分校（UIUC）的 Vikram Adve 和 Chris Lattner
主持的研究项目。最初的动机很朴素：当时大多数编译器（如 GCC）的中间表示是 **语言相关** 且 **紧耦合** 的，
这意味着如果你想为一种新语言构建编译器，或者想在一个新的硬件平台上做代码生成实验，
往往需要从头写大量代码。

Chris Lattner 在 2002 年的硕士论文中提出了 LLVM 的核心设计 —— 一个语言无关、
类型安全、低层次的中间表示（IR），以及围绕它构建的模块化编译基础设施。
2003 年，LLVM 首次公开发布。2005 年，Apple 雇佣了 Chris Lattner，将 LLVM 用于
其开发工具链（Xcode 中的 Clang 替代 GCC）。

"LLVM" 最初是 **Low Level Virtual Machine**\ （底层虚拟机）的缩写。但这个名称很快
就显得过时了——"Virtual Machine" 这个后缀容易让人联想到 Java 虚拟机，而 LLVM 的
核心贡献在于 **编译器基础设施** 而非虚拟机。到 2011 年左右，LLVM 官方正式宣布
"LLVM" 不再是缩写，而是项目的品牌名称，它代表的是整个编译器生态。

LLVM 的重要里程碑：

.. list-table::
   :header-rows: 1

   * - 年份
     - 事件
   * - 2000
     - Chris Lattner 开始 LLVM 项目（UIUC 研究项目）
   * - 2003
     - LLVM 首次公开发布，采用开源许可证
   * - 2005
     - Apple 雇佣 Chris Lattner，LLVM 进入工业界
   * - 2007
     - Clang 前端项目启动，目标替代 GCC
   * - 2011
     - LLVM 3.0 发布，"LLVM" 正式成为品牌名而非缩写
   * - 2012
     - LLVM 获得 ACM Software System Award
   * - 2015
     - LLVM 基金会成立，托管 LLVM 及相关项目
   * - 2020
     - LLVM 迁移到 GitHub，采用更加开放的治理模式
   * - 2025
     - LLVM 22.x 发布，支持更多后端架构与优化技术

为什么 LLVM 能成功？关键在于它解决了传统编译器中的一个痛点： **中间表示的可复用性** 。
在 GCC 中，每个前端（C、C++、Fortran、Ada 等）都有自己的中间表示（GENERIC、GIMPLE、
RTL 等），优化器和后端需要为每种中间表示分别实现。这意味着每增加一种语言前端，
优化器和后端的工作量就成倍增加。这就是编译器的 **N × M 问题**——N 种语言前端 ×
M 种目标后端 = N × M 个"翻译对"需要维护。

.. rst-class:: center

   传统编译器：N × M 种语言-目标组合，需要维护 N × M 个翻译对

.. figure:: /_static/figures/llvm_ecosystem.svg
   :align: center
   :alt: LLVM 项目生态
   :width: 85%

   LLVM 三阶段架构：前端 → LLVM Core → 后端 + 工具链

LLVM 的解法很简洁：统一 IR = N + M。你只需要实现 N 个前端（生成 IR）和 M 个后端
（消费 IR），优化器在 IR 上无论做多少变换，都和前端、后端无关。这个设计看似简单，
却是 LLVM 成功的最核心原因。你在书中看到的所有后续技术——Pass 框架、指令选择、
JIT 编译——都建立在这个前提之上。

这一点我们在下一节架构概览中会深入展开。

LLVM 生态全景
================

今天的 LLVM 已经远不止是编译器基础设施，它形成了一套完整的 **开源编译器生态** 。
核心项目包括：

Clang — C/C++/Objective-C 前端
    最广为人知的 LLVM 子项目。Clang 的设计目标是替代 GCC，提供更快的编译速度、
    更清晰的诊断信息（错误提示）和更模块化的代码结构。
    Clang 的入口在 ``clang/tools/driver/driver.cpp`` ，
    整个前端包括词法分析、语法分析、语义分析和代码生成，我们在第 3 章会详细分析。

LLDB — 调试器
    基于 LLVM 和 Clang 构建的调试器，使用 Clang 的解析器解析表达式，
    使用 LLVM 的底层 API 处理调试信息。相比 GDB，LLDB 的优势在于
    更快的启动速度和更低的内存占用。

libc++ / libc++abi — C++ 标准库实现
    从零实现的 C++ 标准库，注重性能和对最新 C++ 标准的支持。
    很多 LLVM 目标平台（如 iOS、Android）的默认 C++ 标准库就是 libc++。

compiler-rt — 运行时库
    提供编译器所需的运行时支持函数，包括：

    - 软浮点模拟（ ``__addsf3`` 、 ``__muldf3`` 等）
    - 地址消毒剂（AddressSanitizer）和线程消毒剂（ThreadSanitizer）
    - 覆盖率检测（SanitizerCoverage）

MLIR — 多级中间表示框架
    2019 年推出的子项目，旨在解决机器学习框架中"翻译层过多"的问题。
    MLIR 允许定义多级 IR，逐步将高层次算子降低到硬件指令。
    TensorFlow、PyTorch 等框架都在使用 MLIR 来优化计算图到硬件的编译过程。

LLD — 链接器
    从零实现的链接器，比传统 GNU ld 快数倍。LLD 支持 ELF、COFF、Mach-O、
    WebAssembly 等多种目标文件格式，是很多 LLVM 后端的默认链接器。

OpenMP — 并行编程支持
    Clang 中的 OpenMP 实现，支持 ``#pragma omp parallel for`` 等并行指令。

这些子项目的源码都在同一个 ``llvm-project`` 仓库中，按目录组织：\ ``clang/`` 、
``lldb/`` 、 ``libcxx/`` 、 ``compiler-rt/`` 、 ``mlir/`` 、 ``lld/`` 等。
这种单仓库（monorepo）的组织方式保证了各子项目之间的版本一致性。

以 LLVM 22.1.8 为例，版本号定义在 ``cmake/Modules/LLVMVersion.cmake`` 中：

.. code-block:: cmake
   :caption: cmake/Modules/LLVMVersion.cmake

   set(LLVM_VERSION_MAJOR 22)
   set(LLVM_VERSION_MINOR 1)
   set(LLVM_VERSION_PATCH 8)

这个版本号在构建时被嵌入到 ``llvm-config.h`` 中（生成自
``llvm/include/llvm/Config/llvm-config.h.cmake`` ），工具可以通过
``LLVM_VERSION_STRING`` 宏获取。当我们运行 ``clang --version`` 时，
看到的版本号就来自这里。

LLVM 的许可证是 Apache 2.0 with LLVM Exceptions（见 ``llvm/LICENSE.TXT`` ），
它比纯 Apache 2.0 多了一个例外条款：允许你直接用 LLVM 编译出来的目标代码
（如 .o 文件、可执行文件）不受许可证限制，无需因"衍生作品"而开源你的代码。
这是 LLVM 能在工业界广泛采用的重要因素之一——商业软件可以放心使用 LLVM 编译
自己的代码，而不用担心被强制开源。

LLVM 在工业界和学术界的应用
==============================

LLVM 的应用场景远超传统的"编译代码"：

工业界
    编译器
        Apple 的 Xcode 使用 Clang/LLVM 作为默认编译器，Apple 的 Swift 语言
        编译器也基于 LLVM。Android NDK 提供 Clang 作为原生开发工具链。
        Chrome 和 Firefox 等浏览器使用 Clang 来编译 C++ 代码，并利用
        AddressSanitizer 等工具进行内存错误检测。

    GPU 计算
        NVIDIA 的 CUDA 编译器（NVCC）底层使用 LLVM 做代码生成。
        AMD 的 ROCm 编译器栈同样基于 LLVM。

    编程语言
        Rust 编译器（rustc）使用 LLVM 作为后端代码生成器。
        Julia 的 JIT 编译基于 LLVM。Swift 的编译器也使用 LLVM 后端。
        Zig 语言使用 LLVM 作为后端，它的编译速度比 C 编译器还快。

    机器学习
        TensorFlow 的 XLA 编译器使用 LLVM 将计算图编译到 GPU 和 CPU。
        PyTorch 的 TorchScript JIT 编译也使用 LLVM。

学术界
    在编程语言和编译器研究领域，LLVM 几乎成了"标准实验平台"：

    - 新语言的原型实现：论文中常出现"我们基于 LLVM 实现了 X 语言的编译器"
    - 编译优化研究：在 LLVM Pass 中实验新的优化算法
    - 软件安全：利用 LLVM 进行程序分析和加固（如控制流完整性检查）
    - 程序分析：基于 LLVM IR 的静态分析工具

从数据上看，LLVM 的社区规模相当庞大：

- GitHub 上 ``llvm/llvm-project`` 仓库有超过 30k 星标
- 贡献者超过 3000 人（截至 LLVM 22.x 版本）
- 每年举办 LLVM Developers' Meeting，汇集全球的编译器开发者
- LLVM 的论文被引用超过 10000 次

为什么 LLVM 在学术界也如此流行？原因在于它的 **模块化设计** ：你可以只取 LLVM 的
IR 库和 Pass 框架，不用管前端和后端，就能实验自己的优化算法。这种"即插即用"的
特性让 LLVM 成了编译器领域的 **Linux 内核**——它不是唯一的，但它是事实上的标准。

.. note::

   如果你在 ``llvm-project/llvm/CREDITS.TXT`` 中浏览，会看到从 LLVM 创始之初就参与
   的核心贡献者列表。Vikram Adve 的描述是 "provider of much wisdom, and motivator for LLVM"，
   这恰好说明了 LLVM 从学术研究起步、逐步走向工业统治地位的历程。

.. admonition:: 你知道吗？LLVM 名字的由来
   :class: note

   **LLVM** 最初是 **Low Level Virtual Machine** （底层虚拟机）的缩写。
   这个名字来自 Chris Lattner 在 2000 年 UIUC 的硕士论文——他当时想做一个
   "可以在运行时优化任何语言的虚拟机"。

   但讽刺的是，随着 LLVM 的发展，它越来越不像一个"虚拟机"了——它没有
   自己的字节码格式，也不强制沙箱执行。2011 年，LLVM 正式宣布
   **LLVM 不再是缩写** ，它只是一个品牌名。

   所以今天的 LLVM 是一个"名字已经不代表原意的项目"——有点像 GNU，但至少
   GNU 还有个递归定义（GNU's Not Unix）。

.. raw:: html

   <hr>
   <p><em>生成日期: 2026-07-08 &nbsp;&nbsp; 项目: 浅入深出 LLVM</em></p>
