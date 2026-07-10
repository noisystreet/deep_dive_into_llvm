.. _chapter-09-05-filecheck:

==========================
FileCheck 与测试
==========================

FileCheck 是 LLVM 的主要测试工具。它读取输入文本，检查是否包含（或不包含）
指定的模式。在 LLVM 测试中，FileCheck 被用来验证 ``opt`` 、 ``llc`` 等工具的
输出是否符合预期。

.. rst-class:: center

   FileCheck 是 LLVM 测试体系的核心。写出正确的 FileCheck 匹配模式，
   是每个 LLVM 贡献者的必备技能。

为什么需要 FileCheck？
============================

想象你编写了一个新的优化 Pass，你想验证它是否工作。一个直观的方法是：

1. 准备测试输入（IR 文件）
2. 运行你的 Pass
3. 检查输出中是否包含预期结果

FileCheck 就是为这个场景量身定做的工具。它不是 shell 命令比较（ ``diff`` ），
而是 **模式匹配**——你告诉 FileCheck 在输出中"找什么"。

基本用法
============

.. code-block:: llvm
   :caption: test/add.ll

   ; RUN: opt -passes='instcombine' -S %s | FileCheck %s

   define i32 @test(i32 %x) {
       %a = add i32 %x, 0
       ; CHECK: %a = add i32 %x, 0
       ret i32 %a
   }

运行测试：

.. code-block:: console

   $ llvm-lit test/add.ll
   -- Testing: 1 tests, 1 threads --
   PASS: LLVM :: test/add.ll (1 of 1)

``RUN:`` 指令告诉 ``llvm-lit`` 如何运行测试。 ``%s`` 是当前测试文件的路径。
``| FileCheck %s`` 表示将 ``opt`` 的输出用 FileCheck 检查，匹配模式
写在测试文件中。

核心匹配指令
================

.. list-table:: FileCheck 匹配指令
   :header-rows: 1

   * - 指令
     - 含义
     - 示例
   * - ``CHECK``
     - 在输出中查找指定模式
     - ``; CHECK: define i32 @test``
   * - ``CHECK-NOT``
     - 确保输出中 **不包含** 指定模式
     - ``; CHECK-NOT: alloca``
   * - ``CHECK-NEXT``
     - 模式必须出现在 **下一行**
     - ``; CHECK-NEXT: ret i32 %x``
   * - ``CHECK-SAME``
     - 模式必须出现在 **同一行** 的后续位置
     - ``; CHECK-SAME: align 8``
   * - ``CHECK-LABEL``
     - 标记区段的开始
     - ``; CHECK-LABEL: @test``
   * - ``CHECK-DAG``
     - 模式出现在任意位置（不要求顺序）
     - ``; CHECK-DAG: %a = add``

``CHECK`` 的匹配原则：

- 如果输入中有多行匹配，FileCheck 会 **依次消费** 每个模式
- 第一个 ``CHECK`` 匹配第一处，第二个 ``CHECK`` 匹配第二处，以此类推
- 顺序很重要：默认情况下，匹配模式必须按顺序出现

``CHECK-NEXT`` 与 ``CHECK-SAME``
========================================

这两个指令确保相邻匹配之间的空白行行为是确定的：

.. code-block:: llvm

   ; CHECK-LABEL: @test
   ; CHECK: %a = add i32 %x, 0
   ; CHECK-NEXT: ret i32 %x    ; 下一行必须是 ret

   ; CHECK-SAME: {{.*}} = add  ; 同一行上的后续匹配

``CHECK-LABEL`` 用于 **分隔区段** 。它匹配一个标签（如函数定义），然后重置
后续 CHECK 的匹配位置。这在测试多个函数的输出时非常有用：

.. code-block:: llvm

   ; CHECK-LABEL: @add
   ; CHECK: add i32
   ; CHECK: ret i32

   ; CHECK-LABEL: @sub
   ; CHECK: sub i32
   ; CHECK: ret i32

如果没有 ``CHECK-LABEL`` ，第二个函数的 CHECK 指令可能错误地匹配到第一个函数中。

``CHECK-DAG`` ：无顺序匹配
================================

当输出中的多行顺序不确定时，使用 ``CHECK-DAG`` ：

.. code-block:: llvm

   ; 优化后的 IR 中，多个全局变量的顺序可能随机
   ; CHECK-DAG: @g1 = global i32 0
   ; CHECK-DAG: @g2 = global i32 0
   ; CHECK-DAG: @g3 = global i32 0

``CHECK-DAG`` 在指定的区间内查找所有模式，不要求顺序。但要注意：
``CHECK-DAG`` 块之间的顺序要求仍然生效。

正则表达式与变量替换
=========================

FileCheck 支持正则表达式来匹配不确定的值：

.. code-block:: llvm

   ; 匹配任何整数常量
   ; CHECK: add i32 %x, [[#]]]

   ; 使用变量捕获并引用
   ; CHECK: [[REG:r[0-9]+]] = add i32
   ; CHECK-NEXT: mul i32 [[REG]], 2

常见的变量模式：

.. list-table:: FileCheck 变量模式
   :header-rows: 1

   * - 语法
     - 含义
     - 示例
   * - ``[[#]]]``
     - 匹配任意整数
     - ``%x = add i32 42, 1``
   * - ``[[#NUM]]]``
     - 匹配整数并命名为 NUM
     - 后续用 ``[[NUM]]`` 引用
   * - ``[[STRING:.*]]``
     - 匹配任意字符串并命名为 STRING
     - 后续用 ``[[STRING]]`` 引用
   * - ``[[REG:%[a-z]+]]``
     - 匹配 SSA 寄存器名
     - ``[[REG]] = add``
   * - ``{{\[\[}}``
     - 匹配字面量 ``[[``
     - 元字符转义

一个完整的 FileCheck 测试示例：

.. code-block:: llvm
   :caption: test/identity-prop.ll

   ; RUN: opt -load-pass-plugin=%libdir/libIdentityProp.so \
   ; RUN:     -passes='identity-prop' -S %s | FileCheck %s

   define i32 @test(i32 %a, i32 %b) {
   ; CHECK-LABEL: @test
   ; CHECK:         %b
   ; CHECK-NEXT:    ret i32 %b

       %1 = add i32 %b, 0    ; 被替换为 %b
       %2 = mul i32 %a, 1    ; 被替换为 %a
       %3 = add i32 %1, %2
       ret i32 %3
   }

lit 测试框架
================

``lit`` （LLVM Integrated Tester）是 LLVM 的测试运行器。它发现测试文件，
执行 ``RUN:`` 指令，并报告结果。

.. code-block:: console

   # 运行单个测试
   $ llvm-lit test/Transforms/InstCombine/add.ll

   # 运行整个测试目录
   $ llvm-lit test/Transforms/InstCombine/

   # 并行运行测试
   $ llvm-lit -j8 test/

   # 查看测试的详细信息
   $ llvm-lit -v test/Transforms/InstCombine/add.ll

lit 通过 ``RUN:`` 指令中的 ``%s`` 、 ``%t`` 、 ``%S`` 等替换符来参数化测试：

- ``%s`` ：当前测试文件的路径
- ``%t`` ：临时文件路径（用于输出重定向）
- ``%S`` ：测试文件所在的目录
- ``%llvm_tblgen`` ：llvm-tblgen 工具的路径

常见的测试模式
==================

.. code-block:: llvm

   ; 验证优化后 alloca 应该被消除
   ; CHECK-NOT: alloca

   ; 验证某个 Pass 确实执行了
   ; CHECK: Number of instructions deleted: {{[1-9]}}

   ; 验证内联发生了（没有 call 指令了）
   ; CHECK-NOT: call

   ; 验证向量化后的代码中出现了向量类型
   ; CHECK: <4 x i32>

在 LLVM 源码树中的位置
==============================

.. code-block:: text

   llvm/test/
   ├── Transforms/       # 优化 Pass 测试
   │   ├── InstCombine/
   │   ├── GVN/
   │   └── LoopUnroll/
   ├── CodeGen/          # 后端代码生成测试
   │   ├── X86/
   │   ├── AArch64/
   │   └── RISCV/
   ├── MC/               # MC 层测试
   └── tools/            # 工具测试

这些目录中的测试文件是学习 FileCheck 模式的最佳教材。

.. rubric:: 进一步阅读

- `FileCheck 文档 <https://llvm.org/docs/CommandGuide/FileCheck.html>`_ — 命令参考
- `LLVM Testing Infrastructure Guide <https://llvm.org/docs/TestingGuide.html>`_ — LLVM 测试体系
- `llvm-mca 用户指南 <https://llvm.org/docs/CommandGuide/llvm-mca.html>`_ — 机器码分析器
