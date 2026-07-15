.. _chapter-09-02-llc:

==========================
llc：LLVM 静态编译器
==========================

``llc`` 是 LLVM 后端的命令行入口，它将 LLVM IR 编译为目标汇编代码或目标文件。

.. rst-class:: center

   ``opt`` 操作 IR， ``llc`` 把 IR 变成机器码——一个优化，一个生成。

为什么要 llc？
====================

在传统的编译器中，从 IR 到机器码的转换是一个黑盒——你输入 IR，得到二进制，
中间发生了什么只有编译器开发者知道。

LLVM 的设计哲学是 **"没有黑盒"** 。``llc`` 把后端流水线拆解成一系列可观察、
可控制的阶段，让你可以在每个阶段停下来查看状态。这是一个重要的设计决策：
**编译器的后端不是一次性黑盒，而是一系列可组合的变换**。

.. admonition:: llc 与 GCC 的对比
   :class: note

   GCC 的 ``cc1`` 后端同样可以生成汇编，但 LLVM 的 ``llc`` 有几个独特优势：

   - **阶段可观察性**：用 ``-stop-after=`` 可以在任意阶段暂停
   - **跨平台为第一性**：``-march=`` 切换目标架构，LLVM 从设计上就是
     交叉编译器，不需要额外安装交叉工具链
   - **IR 即边界**：所有后端输入都是 LLVM IR，不存在"前端与后端绑定"的问题

基本用法
============

``llc`` 的输入始终是 LLVM IR（文本 ``.ll`` 或比特码 ``.bc``），输出可以是
汇编文本或目标文件：

.. code-block:: console

   # 汇编文本（人类可读，用于调试）
   $ llc input.ll -o output.s

   # 目标文件（机器码字节，用于链接）
   $ llc -filetype=obj input.ll -o output.o

为什么需要区分 ``.s`` 和 ``.o`` ？汇编文本是 **调试后端** 的利器——
你可以打开文件逐行查看每条指令的编码、操作数、寻址模式。目标文件是
**最终产物**——直接喂给链接器（LLD 或 GNU ld）。

相比之下，GCC 需要两步（``gcc -S`` 生成汇编，再用 ``as`` 汇编），
而 ``llc`` 一步完成，且 ``-S`` 和 ``-filetype=obj`` 是同一流水线的
两个输出格式，而不是两个工具。

目标架构选择：跨平台的设计哲学
====================================

LLVM 从第一天起就设计为 **交叉编译器**。在其他编译器中，交叉编译意味着
下载庞大的交叉工具链；在 LLVM 中，只需要一个 ``-march`` 参数：

.. code-block:: console

   # 指定目标架构
   $ llc -march=x86-64 input.ll
   $ llc -march=aarch64 input.ll
   $ llc -march=riscv64 input.ll

   # 指定处理器型号
   $ llc -march=x86-64 -mcpu=skylake input.ll
   $ llc -march=aarch64 -mcpu=cortex-a76 input.ll

   # 启用/禁用特定 CPU 特性
   $ llc -mattr=+avx2,-sse input.ll

   # 查看特定 CPU 的支持特性
   $ llc -mcpu=help

.. admonition:: 为什么 LLVM 的交叉编译如此简单？
   :class: tip

   GCC 的交叉编译器需要为每个目标单独编译一个 ``cc1`` 二进制，因为
   GCC 的后端在编译期就固定了目标架构。LLVM 的 TargetMachine 是
   **运行时选择的**——同一个 ``llc`` 二进制，启动时根据 ``-march``
   加载对应的 Target 描述（通过 TableGen 生成的数据表），而不需要
   重新编译。

   这意味着你只需要一个 ``llc`` 二进制，就可以为 **所有 LLVM 支持**
   的目标架构生成代码。这是 LLVM 模块化架构的直接体现。

控制代码生成阶段：后端流水线的"手术刀"
============================================

``llc`` 最强大的设计之一是 **"流水线阶段可观察性"**——你可以在后端的
任意阶段暂停流水线，查看中间状态。这个设计源于一个核心理念：**编译器
不应该有黑盒**。

.. code-block:: console

   # 在某个阶段之后停止
   $ llc -stop-after=selectiondag input.ll    # DAG 选择后
   $ llc -stop-after=post-rasched input.ll    # 寄存器分配后

   # 从某个阶段开始
   $ llc -start-after=codegen-prepare input.ll

   # 打印每个阶段之后的 IR
   $ llc -print-after-all input.ll

   # 打印机器指令表示
   $ llc -show-mc-inst input.ll

   # 查看编码后的字节
   $ llc -show-encoding input.ll

   # 查看 DAG 图（需要 Graphviz）
   $ llc -view-dag-combine1-dags input.ll
   $ llc -view-sched-dags input.ll

``-stop-after`` 和 ``-start-after`` 是后端调试的"手术刀"：

- 当怀疑指令选择有 bug → 停在 ``selectiondag`` 看 DAG 节点
- 当怀疑寄存器分配有 bug → 停在 ``post-rasched`` 看分配结果
- 搭配 ``-print-after-all`` 可以观察 **每个阶段 IR 的变化轨迹**，
  这在调试新后端或新优化时是无价之宝

如果你熟悉 GDB 的断点调试，可以把 ``-stop-after`` 理解为 **编译器的
断点**——后端流水线的每个阶段都是一个可停靠的站点。

代码生成选项：性能与速度的权衡
========================================

后端代码生成不是"一元优化"——它在 **编译速度** 和 **生成代码质量**
之间做权衡。``llc`` 的代码生成选项反映了这个权衡：

.. code-block:: console

   # 选择寄存器分配器
   $ llc -regalloc=greedy input.ll   # 默认（高质量，编译慢）
   $ llc -regalloc=basic input.ll    # 快速（-O0，编译快）
   $ llc -regalloc=fast input.ll     # 极简（最快速）

   # 选择指令调度策略
   $ llc -misched=ilp input.ll       # 最大化 ILP（默认）
   $ llc -misched=linearize input.ll # 线性化
   $ llc -pre-RA-sched=source input.ll  # 保持顺序

   # 输出文件类型
   $ llc -filetype=asm input.ll      # 汇编文本（默认）
   $ llc -filetype=obj input.ll      # 目标文件

   # 调试信息
   $ llc -asm-verbose input.ll       # 详细的汇编注释
   $ llc -debug input.ll             # 调试输出
   $ llc -stats input.ll             # 统计信息

   # 禁用特定优化
   $ llc -disable-fp-elim input.ll   # 保留帧指针
   $ llc -enable-unsafe-fp-math input.ll  # 不安全浮点优化

寄存器分配器是后端中 **编译时间 vs 代码质量** 权衡最明显的例子：

- ``greedy``：全局贪心分配，考虑活跃区间干涉，生成高质量代码，但编译慢
- ``basic``：一个简单的线性扫描分配器，编译快但代码质量差
- ``fast``：极简分配器，几乎不做全局分析，主要用在调试

选择哪个取决于你的场景：生产构建用 ``greedy``\ ，开发调试用 ``basic``
或 ``fast``\ （快进快出）。

输出格式控制
================

.. code-block:: console

   # 选择汇编语法风格
   $ llc -x86-asm-syntax=att input.ll   # AT&T 语法（Linux 默认）
   $ llc -x86-asm-syntax=intel input.ll  # Intel 语法

   # 控制代码模型
   $ llc -code-model=small input.ll     # small（默认，2GB 内寻址）
   $ llc -code-model=large input.ll     # large（任意地址）
   $ llc -code-model=kernel input.ll    # kernel（内核空间）

   # 重定位模型
   $ llc -relocation-model=pic input.ll # 位置无关代码（PIC）
   $ llc -relocation-model=static input.ll

.. admonition:: 代码模型是什么？
   :class: note

   代码模型（Code Model）是编译器后端的一个概念，表示生成的代码对
   地址空间的假设。``small`` 模型假设代码 + 数据的总大小不超过 2GB，
   所有跳转可以用相对寻址（这是最常用的模型）。``large`` 模型不做
   任何假设，可以访问任意地址，但代价是每条地址访问都需要更多指令。
   这本质上是一个 **"大多数情况下的优化"**——LLVM 把"小"作为默认，
   因为绝大多数程序都满足 2GB 限制。

实战：从 C 源码到汇编的完整流程
=========================================

.. code-block:: console

   $ cat add.c
   int add(int a, int b) {
       return a + b + 42;
   }

   # 生成 IR
   $ clang -S -emit-llvm -O2 add.c -o add.ll

   # 生成 ARM64 汇编
   $ llc -march=aarch64 add.ll -o add_arm64.s
   $ cat add_arm64.s
   add     w0, w0, w1
   add     w0, w0, #42
   ret

   # 生成 RISC-V 汇编
   $ llc -march=riscv64 add.ll -o add_riscv.s
   $ cat add_riscv.s
   add     a0, a0, a1
   addi    a0, a0, 42
   ret

对比同一份 IR 在不同平台上生成的代码，可以直观地感受 LLVM 的 **"一次编写 IR，
处处代码生成"**——同一份 ``add.ll`` 在 ARM64 上生成了 ``add/add/ret``，
在 RISC-V 上生成了 ``add/addi/ret``，语义相同，指令不同。

这是 LLVM 后端最大的价值：**你只需要写一次前端，就能得到所有后端的支持**。
``llc`` 是这个哲学的直接体现——它把后端的全部能力暴露给开发者，让"编译成
机器码"这件事变得透明、可控、可调试。

在源码中的位置：`llvm/tools/llc/llc.cpp <file:///workspace/llvm-project/llvm/tools/llc/llc.cpp>`__