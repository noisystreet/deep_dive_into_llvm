.. _mlir-08-08-01:

====================
MyDSL 设计
====================

本章将通过一个完整的实战项目——**MyDSL** （一个微型领域特定语言），
带你走通自定义 Dialect 从设计到集成的全过程。

.. rst-class:: center

   从零开始构建一个 MLIR Dialect：设计 → 定义 → 降级 → 集成。

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
- **square**：``result = x * x``

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

1. **单一职责**：每个 Operation 做一件事
2. **可降级性**：确保 Operation 可以完整降级到目标 Dialect
3. **验证完整**：在 ODS 中定义充分的验证规则
4. **文档同步**：ODS 中的 `summary` 和 `description` 是自动文档来源

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
