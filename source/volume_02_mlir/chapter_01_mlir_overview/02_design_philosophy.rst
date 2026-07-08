.. _mlir-01-01-02:

===================
MLIR 的设计哲学
===================

上一节我们看到了 MLIR 的动机：传统编译器需要一个可扩展的多层 IR 框架。
本节深入 MLIR 的核心设计哲学——这些哲学贯穿了整个 MLIR 的设计和实现。

.. rst-class:: center

   MLIR 最核心的设计原则是：**渐进降级** （Progressive Lowering）和
   **第一类 Dialect 机制** （First-class Dialects）。

Progressive Lowering（渐进降级）
======================================

**渐进降级**是 MLIR 最重要的设计哲学。它指的是：**不要求从源语言一步降到
机器码，而是通过多层 IR，逐步降低抽象级别，每一层都在合适的粒度上进行优化**。

对比两条路径：

.. code-block:: text

   传统方式（一步到底）：
     Python 源码 → LLVM IR → 机器码
                     ↑
             在 LLVM IR 上做所有优化

   MLIR 方式（渐进降级）：
     Python 源码 → HLO（高级操作）→ linalg（线性代数）→ scf（控制流）
                 → arith（算术）→ LLVM Dialect → LLVM IR → 机器码
                    ↑            ↑            ↑
                高级优化      中层优化     底层优化

每一层的典型优化：

.. list-table:: 各抽象层次的典型优化
   :header-rows: 1

   * - 层次
     - 典型 Dialect
     - 典型优化
   * - 最上层（领域特定）
     - TOSA、StableHLO
     - 算子融合、算子替换、常量折叠
   * - 中层（结构化）
     - linalg、scf、tensor
     - 循环分块（Tiling）、循环融合、内存规划
   * - 底层（标量）
     - arith、memref、LLVM
     - 常数传播、死代码消除、指令选择

最高层的 Dialect 直接对应源语言的语义——比如 TOSA 中一个 ``matmul`` 操作
对应一次矩阵乘法。优化器不需要猜测"这堆 add/mul 是不是矩阵乘法"。

First-class Dialect（第一类方言）
=========================================

MLIR 中的 **Dialect** （方言）是 MLIR 框架中最核心的扩展机制。一个 Dialect
定义了一组 Operation、Type、Attribute，以及它们的语义。

Dialect 是"第一类"（first-class）的——这意味着：

1. **MLIR 框架对任何 Dialect 一视同仁**：没有"内建"和"第三方"的区别
2. **用户自定义的 Dialect 和 MLIR 内置的 Dialect 享有完全相同的地位**
3. **Dialect 之间的转换通过显式的 Lowering Pass 完成**

.. code-block:: text

   // Dialect 在 MLIR 中的表示：
   // 每个操作都以 dialect_name.op_name 的形式命名
   %0 = arith.addi %a, %b : i32        // arith Dialect 的加法
   %1 = scf.for %i = %0 to %n step %s  // scf Dialect 的循环
   %2 = linalg.matmul %A, %B            // linalg Dialect 的矩阵乘法

   格式：dialect.operation 参数列表 : 结果类型

区分不同 Dialect 的操作是有意义的——因为优化器可以根据操作所属的 Dialect
来判断它蕴含的语义。

SSA 作为基础，但不强制
==================================

LLVM IR 要求严格遵循 SSA 形式——每个值恰好定义一次。MLIR 不同：
**MLIR 的 Operation 之间基于 SSA 的 Value 传递数据，但 Operation 内部
的 Region 可以使用自己的控制流约定**。

.. code-block:: text

   // MLIR 中可以使用 SSA 值
   %c = arith.addi %a, %b : i32

   // scf.for 使用 Region（而非 phi 节点）表示循环
   %sum = scf.for %i = %c0 to %n step %c1
       iter_args(%acc = %c0) -> i32 {
       %v = arith.addi %acc, %i : i32
       scf.yield %v : i32
   }

这个设计既保留了 SSA 的优点（明确的 def-use 链），又允许更自然地表达
控制流结构（Region 中的 Block 可以有自己的参数）。

Dialect 的互操作性
======================

不同的 Dialect 可以共存于同一个 MLIR 模块中：

.. code-block:: text

   // 一个混合 Dialect 的程序
   func.func @main(%A: tensor<4x4xf32>, %B: tensor<4x4xf32>)
       -> tensor<4x4xf32> {
       // linalg 级别的矩阵乘法
       %C = linalg.matmul ins(%A, %B: tensor<4x4xf32>, tensor<4x4xf32>)
           outs(%A: tensor<4x4xf32>) -> tensor<4x4xf32>
       func.return %C : tensor<4x4xf32>
   }

混合 Dialect 的模块通过 **Dialect Conversion** 逐步降级——先将 linalg 降到 scf，
再将 scf 降到 cf/arith，最后将 arith 降到 LLVM Dialect。

MLIR 的基础构建块
======================

MLIR 的所有 Dialect 都基于以下四个核心概念：

.. list-table:: MLIR 核心构建块
   :header-rows: 1

   * - 概念
     - 说明
     - 类比 LLVM IR
   * - **Operation**
     - 指令（包括算术、控制流、函数定义等一切）
     - ``Instruction``
   * - **Value**
     - SSA 值，从一个 Operation 流向另一个
     - ``Value`` / ``Use``
   * - **Block**
     - 有序的 Operation 序列，以终止操作结尾
     - ``BasicBlock``
   * - **Region**
     - 一个或多个 Block 的容器
     - （无直接对应，≈ 函数体）

这些概念构成了所有 Dialect 的基础。我们将在第 2 章中深入每个概念。

MLIR 的哲学总结
====================

.. code-block:: text

   1. 渐进降级：不是一步到位，而是逐步降低抽象级别
   2. 第一类 Dialect：用户可定义自己的 IR，与内置 IR 地位平等
   3. ODS 驱动：用 TableGen 描述 Operation，自动生成 C++ 代码
   4. SSA 风格：基于 SSA 的 Value 传递，但允许 Region 内自定义
   5. 可插拔 Pass：优化 Pass 可以在任意抽象级别上定义和运行
   6. 降级至 LLVM：最终可以到达 LLVM Dialect，利用 LLVM 后端

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
