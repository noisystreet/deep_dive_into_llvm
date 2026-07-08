.. _chapter-04-01-pass-intro:

=====================
Pass 框架概述
=====================

前面几章我们一直在用 ``clang`` 和 ``opt`` 这些工具，但有一个关键问题还没讲：
**LLVM 是怎么知道要对 IR 做什么优化的？**

答案就是 **Pass**——LLVM 中所有对 IR 的分析和变换操作都被封装成一个"Pass"。

.. rst-class:: center

   Pass 是 LLVM 优化系统的基本单元。一段 IR 输入，一段 IR 输出，中间夹着
   特定的分析或变换逻辑。

从用户视角看 Pass
====================

如果你用过 ``opt`` 工具，就已经接触过 Pass 了：

.. code-block:: console

   # 运行 mem2reg Pass（将 alloca/load/store 提升为 SSA 值）
   $ opt -passes=mem2reg input.ll -S -o output.ll

   # 运行多个 Pass 组成管道
   $ opt -passes='mem2reg,instcombine,gvn' input.ll -S -o output.ll

   # 查看所有可用的 Pass
   $ opt --print-passes

每个 Pass 做一件**具体且可组合的事**：

- ``mem2reg``：把栈上的 ``alloca`` 提升为 SSA 寄存器
- ``instcombine``：合并/简化指令
- ``gvn`` （Global Value Numbering）：消除冗余计算
- ``dce`` （Dead Code Elimination）：删除死代码
- ``inliner``：函数内联

这些 Pass 可以像搭积木一样组合起来，形成优化管道。这就是 LLVM 优化系统的核心思想。

Pass 的分类
================

LLVM 的 Pass 分为两大类型：

.. list-table:: Pass 类型
   :header-rows: 1

   * - 类型
     - 作用
     - 是否修改 IR
     - 示例
   * - **分析 Pass** （Analysis Pass）
     - 收集 IR 的信息，供其他 Pass 使用
     - 否
     - DominatorTree、LoopInfo、AAResults
   * - **变换 Pass** （Transform Pass）
     - 修改 IR，优化或转换代码
     - 是
     - mem2reg、instcombine、GVN

分析 Pass 和变换 Pass 之间有**依赖关系**——变换 Pass 在执行前可能需要一些分析
Pass 的结果。LLVM 的 Pass 管理器自动处理这些依赖。

Pass 的粒度
================

Pass 可以在三个粒度上运行：

.. list-table:: Pass 运行粒度
   :header-rows: 1

   * - 粒度
     - 说明
     - 使用场景
   * - Module Pass
     - 在整个 Module 上运行一次
     - 全局优化（GlobalDCE、IPO）
   * - Function Pass
     - 在每个 Function 上各运行一次
     - 大多数优化（mem2reg、instcombine）
   * - Loop Pass
     - 在每个 Loop 上各运行一次
     - 循环优化（LICM、IndVarSimplify）

执行顺序：**Module → Function → Loop**，外层的 Pass 可以包含内层的 Pass 管道。

一个简单的 Pass 示例
=========================

以 ``mem2reg`` 为例——它是最常用的 LLVM Pass 之一。看它做了什么：

.. code-block:: llvm

   ; 输入（mem2reg 前）
   define i32 @add(i32 %a, i32 %b) {
       %1 = alloca i32
       store i32 %a, ptr %1
       %2 = alloca i32
       store i32 %b, ptr %2
       %3 = load i32, ptr %1
       %4 = load i32, ptr %2
       %5 = add i32 %3, %4
       ret i32 %5
   }

运行 ``opt -passes=mem2reg`` 后：

.. code-block:: llvm

   ; 输出（mem2reg 后）
   define i32 @add(i32 %a, i32 %b) {
       %add = add i32 %a, %b
       ret i32 %add
   }

``mem2reg`` 识别出 ``a`` 和 ``b`` 只是简单的传值，不需要走内存，直接把它们提升为
SSA 值。这简化了后续优化——因为 SSA 形式比 ``alloca/load/store`` 更容易分析。

Pass 管理器的职责
=====================

Pass 管理器（Pass Manager）负责：

1. **调度**：按正确的顺序执行 Pass
2. **依赖管理**：在执行变换 Pass 之前，先运行其依赖的分析 Pass
3. **缓存**：如果多个变换 Pass 依赖同一个分析结果，避免重复计算
4. **失效**：当变换 Pass 修改了 IR，通知相关的分析 Pass 结果已失效

LLVM 有两代 Pass 管理器：**Legacy Pass Manager** （已弃用）和 **New Pass Manager** （当前标准）。
下一节我们详细讲解它们的差异。

从源码理解 Pass
====================

Pass 的基类定义在 LLVM 源码中：

- `llvm/include/llvm/IR/PassManager.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/IR/PassManager.h>`__ —— New PM 的核心接口
- `llvm/include/llvm/Pass.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/Pass.h>`__ —— Legacy PM 的核心接口

.. code-block:: cpp

   // New PM 中一个分析 Pass 的基本接口
   class AnalysisInfoMixin {
       // ...
   };

   // New PM 中一个变换 Pass 的基本接口
   class PassInfoMixin {
       // ...
   };

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
