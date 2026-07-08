.. _mlir-appendix-01-code-reading:

==========================
MLIR 源码阅读指南
==========================

读完第二卷正文后，下一步自然是阅读 ``llvm-project/mlir/`` 源码。
本节提供一份按主题组织的阅读路线图。

.. rst-class:: center

   推荐阅读顺序：``mlir/IR`` → ``mlir/Dialect`` → ``mlir/Conversion`` → ``mlir/Pass``

目录结构
==================

.. code-block:: text

   mlir/
   ├── include/mlir/
   │   ├── IR/                  # 核心 IR 类（Operation, Value, Block, Region）
   │   ├── Dialect/             # 各 Dialect 的头文件和 ODS 生成物
   │   ├── Conversion/          # 跨 Dialect 降级 Pass 声明
   │   ├── Pass/                # Pass 框架
   │   └── ExecutionEngine/     # JIT 执行引擎
   ├── lib/
   │   ├── IR/                  # IR 核心实现
   │   ├── Dialect/             # 各 Dialect 实现
   │   ├── Conversion/          # 降级 Pass 实现
   │   ├── Pass/                # PassManager 实现
   │   └── ExecutionEngine/     # ORC JIT 封装
   ├── examples/
   │   └── toy/                 # 官方端到端 Tutorial（Ch1-Ch7）
   └── docs/
       └── Tutorials/Toy/       # Toy Tutorial 文档

核心 IR 层
==================

建议按以下顺序阅读 ``mlir/include/mlir/IR/`` ：

.. list-table:: IR 核心文件
   :header-rows: 1

   * - 文件
     - 内容
     - 对应章节
   * - ``Operation.h``
     - Operation 类，MLIR 基本执行单元
     - :ref:`mlir-02-02-01`
   * - ``Types.h`` / ``BuiltinTypes.h``
     - 类型系统
     - :ref:`mlir-02-02-02`
   * - ``Region.h`` / ``Block.h``
     - Region 和 Block
     - :ref:`mlir-02-02-03`
   * - ``Location.h``
     - 位置信息与诊断
     - :ref:`mlir-02-02-04`
   * - ``Dialect.h``
     - Dialect 注册机制
     - :ref:`mlir-01-01-02`

Dialect 层
==================

每个 Dialect 通常遵循固定布局：

.. code-block:: text

   mlir/include/mlir/Dialect/<Name>/IR/
   ├── <Name>Ops.td          # ODS 操作定义
   ├── <Name>Dialect.td      # Dialect 声明
   └── <Name>Ops.h           # 生成的 C++ 头文件

重点 Dialect 源码路径：

- **builtin** — `BuiltinOps.td <file:///workspace/llvm-project/mlir/include/mlir/IR/BuiltinOps.td>`__
- **func** — `FuncOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Func/IR/FuncOps.td>`__
- **arith** — `ArithOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Arith/IR/ArithOps.td>`__
- **scf** — `mlir/include/mlir/Dialect/SCF/IR/`
- **linalg** — `mlir/include/mlir/Dialect/Linalg/IR/`

Conversion 层
==================

降级 Pass 集中在 ``mlir/lib/Conversion/`` 。最常用的几条路径：

.. list-table:: 核心 Conversion Pass
   :header-rows: 1

   * - Pass
     - 源码
     - 说明
   * - ``convert-linalg-to-loops``
     - `Loops.cpp <file:///workspace/llvm-project/mlir/lib/Dialect/Linalg/Transforms/Loops.cpp>`__
     - linalg → scf/affine 循环
   * - ``convert-scf-to-cf``
     - `SCFToControlFlow.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/SCFToControlFlow/SCFToControlFlow.cpp>`__
     - scf → cf 控制流
   * - ``convert-arith-to-llvm``
     - `ArithToLLVM.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/ArithToLLVM/ArithToLLVM.cpp>`__
     - arith → LLVM Dialect
   * - ``convert-func-to-llvm``
     - `FuncToLLVM.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/FuncToLLVM/FuncToLLVM.cpp>`__
     - func → LLVM Dialect

Pass 框架
==================

- `Pass.h <file:///workspace/llvm-project/mlir/include/mlir/Pass/Pass.h>`__ — Pass 基类
- `PassManager.h <file:///workspace/llvm-project/mlir/include/mlir/Pass/PassManager.h>`__ — Pass 调度
- `PatternMatch.h <file:///workspace/llvm-project/mlir/include/mlir/IR/PatternMatch.h>`__ — Pattern Rewrite

与第一卷的衔接
==================

.. list-table:: 两卷源码对照
   :header-rows: 1

   * - MLIR 概念
     - LLVM 对应
     - 第一卷章节
   * - ``mlir::PassManager``
     - ``llvm::PassManager``
     - :ref:`chapter-04-03-new-pm`
   * - ``Dialect Conversion``
     - IR 降级 / Legalization
     - :ref:`chapter-07-03-instruction-selection`
   * - ``ExecutionEngine``
     - ORC JIT / LLJIT
     - :ref:`chapter-08-04-lljit-and-lazy`
   * - ``mlir-tblgen``
     - ``llvm-tblgen``
     - :ref:`chapter-06-05-code-generation`

Toy Tutorial 阅读路线
============================

官方 Tutorial 是最佳的端到端源码阅读材料：

.. code-block:: text

   Ch1-Ch2: 前端 AST → MLIR 生成（理解 IR 构建）
   Ch3:     定义 Toy Dialect（理解 ODS）
   Ch4:     添加优化 Pass（理解 Pattern Rewrite）
   Ch5-Ch6: 降级到 LLVM Dialect（理解 Conversion）
   Ch7:     接入 ExecutionEngine（理解 JIT）

入口：`mlir/examples/toy/ <file:///workspace/llvm-project/mlir/examples/toy/>`__

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
