.. _mlir-11-06-01:

==========
降级的概念
==========

降级（Lowering）是 MLIR **渐进式多层 IR** 设计的核心——将高层、领域相关的
IR 逐步转换为更低层、更接近机器表示的 IR。

.. rst-class:: center

   一次性降级（One-shot Lowering）是一次将高层 IR 直接转换为 LLVM IR。
   渐进降级（Progressive Lowering）是通过多层 Dialect，逐层降低抽象级别。

.. admonition:: Progressive Lowering：MLIR 最有影响力的设计哲学
   :class: note

   "一次性降级"（One-shot Lowering）是传统编译器的做法——Clang 一次将
   C++ AST 降级到 LLVM IR，GCC 也是一次将 GIMPLE 降级到 RTL。

   MLIR 提出了一个截然不同的思路：**不要一次降级到底，而是逐层降级** 。
   这样做有三大好处：

   **1. 保留高层语义用于优化**
   在 linalg Dialect 层面做循环分块（tiling）和融合（fusion），比在
   LLVM IR 层面做要容易一百倍。因为 linalg 知道"这是一个矩阵乘法"，
   而 LLVM IR 只看到一堆 load/mul/add/store。

   **2. 减少跨层信息丢失**
   当你把高层 IR 一次降级到底层时，丢失的信息无法恢复。逐层降级可以
   在每一层完成该层的优化后再进入下一层。

   **3. 分而治之的工程优势**
   每层的降级逻辑是独立的——写 ``tosa-to-linalg`` 降级的工程师不需要
   理解 LLVM 寄存器分配。这使得 MLIR 的降级管道可以由不同团队并行开发。

   Progressive Lowering 被广泛认为是 MLIR 对编译器设计领域最重要的
   学术贡献之一。今天，从 TensorFlow 到 PyTorch，从 CIRCT（硬件设计）
   到 IREE（推理引擎），所有基于 MLIR 的项目都采用了这种设计哲学。

一次性降级 vs 渐进降级
==============================

一次性降级是传统编译器的做法（例如 Clang 直接将 C++ 翻译为 LLVM IR）：

.. mermaid::

   flowchart LR
       A[C++ 源码] --> B[Clang AST]
       B --> C[LLVM IR]
       C --> D[机器码]

MLIR 采用渐进降级：

.. mermaid::

   flowchart LR
       A[tensor/linalg] --> B[scf/arith]
       B --> C[cf/LLVM Dialect]
       C --> D[LLVM IR]
       D --> E[机器码]

渐进降级的优势：

.. list-table:: 一次性 vs 渐进
   :header-rows: 1

   * - 特性
     - 一次性降级
     - 渐进降级
   * - 优化粒度
     - 只能在 LLVM IR 级别
     - 每个抽象级别都可优化
   * - 中间表示
     - 丢失高层语义
     - 保留每层语义
   * - 编译器复杂度
     - N 个前端需要 N 条路径
     - 共用低层降级路径
   * - 调试难度
     - 一步到位，难定位
     - 分步验证，易调试

Dialect 之间的边界
=========================

MLIR 的降级路径中，每个 Dialect 负责不同的抽象级别：

.. code-block:: text

   高层（领域特定）
   ┌─────────────────────────────────┐
   │ tensor / linalg / tosa / hlo    │  ← ML 框架表示
   ├─────────────────────────────────┤
   │ scf（结构化控制流）             │  ← 循环展开后
   ├─────────────────────────────────┤
   │ arith / math（算术运算）        │  ← 标量计算
   ├─────────────────────────────────┤
   │ memref（内存抽象）              │  ← 缓冲化后
   ├─────────────────────────────────┤
   │ cf（底层控制流）                │  ← 结构化消失
   ├─────────────────────────────────┤
   │ LLVM Dialect（LLVM IR 映射）    │  ← 最后一步
   ├─────────────────────────────────┤
   │ LLVM IR（.ll 文件）             │
   └─────────────────────────────────┘
   低层（机器相关）

完整的降级路径示例
============================

.. code-block:: console

   # MLIR 到 LLVM IR 的完整降级管道
   $ mlir-opt --one-shot-bufferize \
       --linalg-generalize-named-ops \
       --linalg-lower-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts \
       input.mlir | mlir-translate --mlir-to-llvmir

每一步都是可选的，可以根据需要组合。

降级过程的验证
============================

MLIR 在每次降级步骤后会执行验证器：

- **合法性验证** ：确认目标 Dialect 中 Operation 使用的正确性
- **类型验证** ：检查类型是否匹配
- **SSA 验证** ：确认 SSA 形式的正确性

如果降级过程中某个 Operation 未被正确处理（转换），
``UnrealizedConversionCastOp`` 会残留，导致验证失败：

.. code-block:: text

   // 残留的 UnrealizedConversionCastOp
   %0 = unrealized_conversion_cast %arg0 : tensor<4xf32> to memref<4xf32>
   // ^^^ 这个 cast 必须在最终降级完成后被消除

源码走读：降级管道的代码组织
======================================

MLIR 的每个降级步骤对应一个独立的 Conversion Pass，注册在
`Conversion/Passes.td <file:///workspace/llvm-project/mlir/include/mlir/Conversion/Passes.td>`__ 。
这种模块化组织正是前文"分而治之"工程优势的体现——
``convert-scf-to-cf`` 的实现在 `SCFToControlFlow.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/SCFToControlFlow/SCFToControlFlow.cpp>`__ ，
与 ``convert-arith-to-llvm`` 完全独立。

Toy Tutorial Ch6 的 `LowerToLLVM.cpp <file:///workspace/llvm-project/mlir/examples/toy/Ch6/mlir/LowerToLLVM.cpp>`__
文件头用 ASCII 图描述了多条降级路径的汇合关系——这是理解渐进降级的最佳源码注释之一。

动手验证
==========

用项目 CI 验证的完整管道走一遍端到端流程：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/tensor_add.mlir \
       --one-shot-bufferize=bufferize-function-boundaries \
       --convert-linalg-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-translate --mlir-to-llvmir

也可以运行 ``bash scripts/verify-mlir-examples.sh`` 分步验证各阶段。

本章小结
========

渐进降级的本质是**在正确的抽象层次做正确的优化，然后逐层下沉** 。
理解这个概念后，:ref:`mlir-11-06-02` 至 :ref:`mlir-11-06-04` 的每一步
都有了明确的定位——它们不是随意的 Pass 堆砌，而是精心设计的语义展开链。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
