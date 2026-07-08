.. _mlir-04-04-01:

============
ODS 概述
============

ODS（Operation Definition Spec）是 MLIR 中定义 Operation、Type、Attribute
等的**声明式框架**。它基于 LLVM 的 TableGen 语言，让你用 ``.td`` 文件描述
Operation 的结构和约束，然后由 ``mlir-tblgen`` 自动生成 C++ 代码。

.. rst-class:: center

   第 1 卷中我们介绍了 TableGen——LLVM 中的数据描述语言。MLIR 的 ODS
   将 TableGen 的能力发挥到了极致：从 Operation 定义、验证器、解析/打印、
   到序列化代码，全部自动生成。

.. admonition:: 从 LLVM TableGen 到 MLIR ODS：一个 DSL 的进化
   :class: note

   LLVM 的 TableGen 是一个"通用数据描述语言"，它的设计哲学是：
   给你最小的工具集（Record、Class、DAG），让你自己做任何事。

   MLIR 的 ODS 在 TableGen 之上做了一层**领域专用的抽象**：
   - 不用写 ``def`` 来定义 Operation，而是用 ``Op<>``
   - 参数类型用 ``I32:$lhs`` 而不是 ``Field<I32>``
   - 汇编格式用声明式字符串而不是 C++ 代码片段

   这种"领域特化"带来的好处是惊人的：

   对于 MLIR 内置的 Dialect，ODS 生成的代码量是手写代码的 **5-10 倍**。
   以 ``arith`` Dialect 为例：``ArithOps.td`` 大约有 3000 行 TableGen，
   而 ``mlir-tblgen -gen-op-defs`` 生成的 C++ 代码超过 30000 行。
   换句话说，一顿饭吃 10 分钟，产生的能量够工作 1 小时。

   更关键的是，ODS 生成的代码**不会有人为 bug**。编码表、验证函数、
   解析/打印函数——这些代码的模式高度固定，最适合自动生成。
   历史上 LLVM/MLIR 的很多 bug 都来自手写的解析器或验证器，
   ODS 将这些 bug 类别彻底消灭了。

   后来 MLIR 社区还开发了 **PDL（Pattern Definition Language）**——
   一种用于定义 Rewrite Pattern 的 DSL。PDL 让 Pattern 的编写变得更加
   声明式和可组合。Pattern 的"金矿"——InstCombine——在 MLIR 中有了更
   优雅的写法。

为什么需要 ODS？
====================

编写一个 MLIR Operation 需要大量模板代码：

.. list-table:: 一个 Operation 需要的手写代码
   :header-rows: 1

   * - 组件
     - 手写工作量
     - ODS 自动生成
   * - C++ 类声明
     - ~50 行
     - ✅
   * - 构造函数
     - ~20 行
     - ✅
   * - 参数访问器（getInput、getOutput 等）
     - ~30 行
     - ✅
   * - 汇编格式解析器
     - ~100 行
     - ✅（声明即可）
   * - 汇编格式打印器
     - ~80 行
     - ✅（声明即可）
   * - 验证器
     - ~50 行（需要手写逻辑）
     - ✅（自动生成骨架）
   * - 序列化/反序列化
     - ~50 行
     - ✅

ODS 的核心思路：**只描述"是什么"，自动生成"怎么做"**。

ODS 文件结构
=================

一个典型的 ODS 文件：

.. code-block:: text
   :caption: MyDialect.td

   // 1. 包含 MLIR 基础定义
   include "mlir/IR/OpBase.td"

   // 2. 定义 Dialect
   def MyDialect : Dialect {
       let name = "my_dialect";
       let summary = "My custom dialect";
   }

   // 3. 定义 Operation
   def MyAddOp : Op<MyDialect, "add"> {
       let summary = "Addition operation";

       let arguments = (ins I32:$lhs, I32:$rhs);
       let results = (outs I32:$result);

       let assemblyFormat = "$lhs `,` $rhs attr-dict";
   }

这个 ``.td`` 文件定义了 Dialect 和 Operation，然后由 ``mlir-tblgen``
生成对应的 C++ 代码。

ODS 中的 TableGen 扩展
============================

ODS 扩展了 TableGen 的语法，加入了专门用于 MLIR Operation 定义的构造：

**``Op<>``**：定义 Operation 的基类模板

.. code-block:: text

   def MyOp : Op<Dialect, "op_name"> {
       // dialect 前缀：my_dialect
       // 操作名：my_op
       // 完整名称：my_dialect.my_op
   }

**``ins`` / ``outs``**：定义输入参数和输出结果

.. code-block:: text

   let arguments = (ins I32:$lhs, I32:$rhs);
   // 输入：两个 i32 类型，名字 lhs 和 rhs

   let results = (outs I32:$result);
   // 输出：一个 i32 类型，名字 result

**``let``**：设置 Operation 的属性

.. code-block:: text

   let summary = "Brief description";
   let description = [{
       Longer description that can span
       multiple lines.
   }];
   let assemblyFormat = "$lhs `,` $rhs attr-dict";

ODS 的工作流程
====================

.. mermaid::

   flowchart LR
       A[MyDialect.td] --> B[mlir-tblgen]
       B --> C[MyDialect.h.inc]
       B --> D[MyDialect.cpp.inc]
       C --> E[你的 C++ 代码\n#include 生成的文件]
       D --> E

       style A fill:#ff9800,color:#fff
       style B fill:#4a9eff,color:#fff

1. 编写 ``.td`` 文件
2. 运行 ``mlir-tblgen`` 生成 ``.h.inc`` 和 ``.cpp.inc`` 文件
3. 在你的 C++ 代码中 ``#include`` 这些文件
4. 编译

生成的文件通常包含：

- **Op 类声明** （``MyDialect.h.inc`` ）：Operation 的 C++ 类
- **Op 类实现** （``MyDialect.cpp.inc`` ）：构造函数、解析/打印等
- **Dialect 注册**：Dialect 的初始化代码

ODS vs 手写 C++
====================

ODS 不能覆盖 100% 的代码生成场景。**对于大部分情况（90%+），ODS 足够**。
对于需要手写的场景，可以通过 ODS 中的 ``let verifier`` 或 ``let hasCustomAssemblyFormat``
来插入自定义逻辑。

.. code-block:: text

   def MyOp : Op<MyDialect, "my_op"> {
       // ODS 自动处理大部分代码
       let arguments = (ins I32:$input);
       let results = (outs I32:$output);

       // 自定义验证器（ODS 生成骨架，手写验证逻辑）
       let verifier = [{
           if (getInput().getType() != getOutput().getType())
               return emitOpError("type mismatch");
           return success();
       }];

       // 自定义汇编格式（完全手写）
       let hasCustomAssemblyFormat = 1;
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
