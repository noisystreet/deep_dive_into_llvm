.. _chapter-09-02-llc:

==========================
llc：LLVM 静态编译器
==========================

``llc`` 是 LLVM 后端的命令行入口。它将 LLVM IR 编译为目标汇编代码或目标文件。

.. rst-class:: center

   ``opt`` 操作 IR， ``llc`` 把 IR 变成机器码——一个优化，一个生成。

基本用法
============

.. code-block:: console

   # 将 IR 编译为汇编
   $ llc input.ll -o output.s

   # 将 IR 编译为目标文件
   $ llc -filetype=obj input.ll -o output.o

   # 查看生成的机器码（反汇编）
   $ llc input.ll -o output.s && cat output.s

目标架构选择
================

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

控制代码生成阶段
====================

``llc`` 允许你在后端流水线的某个阶段停止，查看中间结果：

.. code-block:: console

   # 在某个阶段之后停止
   $ llc -stop-after=selectiondag input.ll    # DAG 选择后
   $ llc -stop-after=post-rasched input.ll    # 寄存器分配后

   # 从某个阶段开始
   $ llc -start-after=codegen-prepare input.ll

   # 打印每个阶段的 IR
   $ llc -print-after-all input.ll

   # 打印机器指令表示
   $ llc -show-mc-inst input.ll

   # 查看编码后的字节
   $ llc -show-encoding input.ll

   # 查看 DAG 图（需要 Graphviz）
   $ llc -view-dag-combine1-dags input.ll
   $ llc -view-sched-dags input.ll

代码生成选项
================

.. code-block:: console

   # 选择寄存器分配器
   $ llc -regalloc=greedy input.ll   # 默认（高质量）
   $ llc -regalloc=basic input.ll    # 快速（-O0）
   $ llc -regalloc=fast input.ll     # 极简

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

输出格式控制
================

.. code-block:: console

   # 选择汇编语法风格
   $ llc -x86-asm-syntax=att input.ll   # AT&T 语法（Linux 默认）
   $ llc -x86-asm-syntax=intel input.ll  # Intel 语法

   # 控制代码模型
   $ llc -code-model=small input.ll     # small（默认）
   $ llc -code-model=large input.ll     # large
   $ llc -code-model=kernel input.ll    # kernel

   # 重定位模型
   $ llc -relocation-model=pic input.ll # 位置无关代码（PIC）
   $ llc -relocation-model=static input.ll

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

对比同一份 IR 在不同平台上生成的代码，可以直观地感受 LLVM 的"一次编写 IR，
处处代码生成"。

在源码中的位置：`llvm/tools/llc/llc.cpp <file:///workspace/llvm-project/llvm/tools/llc/llc.cpp>`__
