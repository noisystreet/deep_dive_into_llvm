.. _mlir-09-09-01:

====================
MyDSL 设计
====================

本章将通过一个完整的实战项目——**MyDSL** （一个微型领域特定语言），
带你走通自定义 Dialect 从设计到集成的全过程。

.. rst-class:: center

   从零开始构建一个 MLIR Dialect：设计 → 定义 → 降级 → 集成。

.. admonition:: 自定义 Dialect 的成功案例：从 CIRCT 到 IREE
   :class: tip

   MLIR 的自定义 Dialect 能力催生了几个非常有影响力的项目：

   **CIRCT（Circuit IR Compilers and Tools）**
   CIRCT 是 LLVM 社区下的硬件设计编译器项目。它将 MLIR 引入到硬件
   设计自动化领域，定义了多个用于表示数字电路的 Dialect：
   - ``comb`` ：组合逻辑（AND、OR、XOR 等）
   - ``seq`` ：时序逻辑（寄存器、触发器）
   - ``hw`` ：硬件模块（模块定义、实例化、连线）
   - ``sv`` ：SystemVerilog 输出

   传统上，硬件设计工具链的各种内部格式（Verilog AST、EDIF、Blif）
   互不兼容。CIRCT 通过 MLIR 统一了这些格式——正如 LLVM 统一了
   编程语言编译器一样。

   **IREE（Intermediate Representation Execution Environment）**
   IREE 是 Google 推出的 ML 推理引擎，它使用 MLIR 作为唯一的中间表示
   格式。IREE 定义了多个自定义 Dialect（ ``flow`` 、``hal`` 、``stream`` ）
   来表示内存管理、设备分配和流式执行。

   IREE 的架构是 MLIR "多级 IR" 概念的极致体现：从 StableHLO 到
   ``flow`` （数据流图）到 ``hal`` （硬件抽象层）到 ``stream`` （流执行）
   到 LLVM Dialect 到机器码——一共 6 层 IR，每层负责一个明确的抽象级别。

   这些成功案例说明：**自定义 Dialect 是 MLIR 生态的核心竞争力** 。

MyDSL 的功能
==================

MyDSL 是一个简单的算术 DSL，支持以下功能：

.. code-block:: text

   // MyDSL 程序示例
   func.func @main(%a: i32, %b: i32) -> i32 {
       // 自定义操作：乘加运算
       %0 = my_dsl.mac %a, %b, %a : i32
       // 自定义操作：平方
       %1 = my_dsl.square %0 : i32
       func.return %1 : i32
   }

MyDSL 定义两个自定义 Operation：

- **mac** （multiply-accumulate）：``d = a * b + c``
- **square** ：``result = x * x``

项目结构
================

MyDSL Dialect 在 LLVM 项目中通常的目录结构：

.. code-block:: text

   mydsl/
   ├── include/
   │   └── mydsl/
   │       ├── MyDSLDialect.td     ← ODS 定义 Dialect
   │       ├── MyDSLOps.td         ← ODS 定义 Operation
   │       ├── MyDSLDialect.h      ← Dialect C++ 头文件
   │       └── MyDSLOps.h          ← Op C++ 头文件
   ├── lib/
   │   ├── MyDSLDialect.cpp        ← Dialect 注册
   │   ├── MyDSLOps.cpp            ← Op 实现
   │   └── MyDSLToArith.cpp        ← 降级实现
   └── CMakeLists.txt              ← 构建配置

设计选择
==================

在设计自定义 Dialect 时，需要决定以下问题：

**1. Dialect 的名称和前缀**

.. code-block:: text

   def MyDSL_Dialect : Dialect {
       let name = "my_dsl";
       // 在 IR 中使用：my_dsl.mac, my_dsl.square
   }

**2. Operation 的抽象级别**

MyDSL 的 Operation 位于 `arith` 之上、`tensor` 之下——它们操作标量值，
但表达的是更高级的运算模式。

**3. 降级目标**

MyDSL → `arith` → `LLVM Dialect` → LLVM IR

**4. 验证规则**

.. code-block:: text

   // mac 的验证规则：
   // - 三个操作数必须类型相同
   // - 结果类型必须与操作数相同
   // - 只支持整数类型

设计原则
==================

设计自定义 Dialect 时遵循的原则：

1. **单一职责** ：每个 Operation 做一件事
2. **可降级性** ：确保 Operation 可以完整降级到目标 Dialect
3. **验证完整** ：在 ODS 中定义充分的验证规则
4. **文档同步** ：ODS 中的 `summary` 和 `description` 是自动文档来源

与 Toy Tutorial 的对照
==============================

MyDSL 的设计思路与 LLVM 官方 Toy Tutorial 完全一致。Toy 是 MLIR 自带的
端到端示例，从 Ch1 到 Ch7 循序渐进地构建了一个完整的 Toy 语言编译器：

.. code-block:: text

   mlir/examples/toy/
   ├── Ch1/   # AST 遍历
   ├── Ch2/   # 引入 MLIR 代码生成
   ├── Ch3/   # 定义 Toy Dialect
   ├── Ch4/   # 添加优化 Pass
   ├── Ch5/   # 部分降级
   ├── Ch6/   # 完整降级到 LLVM Dialect
   └── Ch7/   # 接入 JIT 执行

Toy Tutorial 源码入口：
`mlir/examples/toy/README.md <file:///workspace/llvm-project/mlir/examples/toy/README.md>`__

Ch7 的 ``LowerToLLVM.cpp`` 展示了自定义 Dialect 降级的标准写法——
用 ``RewritePatternSet`` 将 ``toy.print`` 等操作替换为 ``llvm`` 操作，
与 :ref:`mlir-11-05-02` 的 Pattern Rewrite 框架直接对应。

MyDSL 与 Toy 的对应关系：

.. list-table:: MyDSL vs Toy Tutorial
   :header-rows: 1

   * - MyDSL 组件
     - Toy 对应文件
     - 说明
   * - ``MyDSLDialect.td``
     - ``Ch3/include/toy/Dialect.td``
     - ODS 定义 Dialect
   * - ``MyDSLOps.td``
     - ``Ch3/include/toy/Ops.td``
     - ODS 定义 Operation
   * - ``MyDSLToArith.cpp``
     - ``Ch6/mlir/LowerToLLVM.cpp``
     - 降级 Pattern 实现
   * - 驱动程序
     - ``Ch7/toyc.cpp``
     - 接入 ``ExecutionEngine`` JIT

建议读者在实现 MyDSL 时，以 Toy Ch3-Ch7 为参考实现对照阅读。
第一卷 :ref:`chapter-06-01-tablegen-intro` 中的 TableGen 基础在此直接派上用场。

动手验证
==========

浏览 Toy 示例源码结构：

.. code-block:: console

   ls llvm-project/mlir/examples/toy/
   # 阅读 Ch3 的 Ops.td，对比本章 MyDSL 的 Operation 设计

本章小结
========

自定义 Dialect 的设计核心是**抽象级别选择**和**降级路径规划** 。
MyDSL 选择了 arith 作为直接降级目标，与 Toy 选择 LLVM Dialect 类似但少了一层。
后续几节将逐步实现 MyDSL 的 ODS 定义和降级逻辑。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
