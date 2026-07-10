.. _mlir-11-07-02:

=================
StableHLO Dialect
=================

StableHLO 是 MLIR 生态中 **最重要的机器学习 Dialect** 之一。它是
HLO（High-Level Operations）的稳定版本，被 TensorFlow、JAX 和 PyTorch
等框架用于表示计算图。

.. rst-class:: center

   StableHLO = HLO 的稳定演进版。它在保持向后兼容的同时提供版本化升级路径。

.. admonition:: 为什么 Google 需要"稳定版 HLO"？
   :class: note

   原始 HLO 随 TensorFlow/XLA 快速迭代，Op 语义和签名频繁变动——
   今天保存的模型，明天可能就解析失败。StableHLO 的核心承诺是
   **版本化兼容性** ：每个程序标注 ``stablehlo.version`` ，旧版本
   程序可以被新版本编译器处理。

   它使用 MLIR Bytecode 格式 ``.mlirbc`` 而非文本 IR 做序列化——
   体积更小、解析更快，适合在生产环境传输和缓存计算图。
   JAX 导出 StableHLO、IREE 导入 StableHLO，形成了 MLIR 生态中
   最活跃的跨框架 IR 交换格式之一。

StableHLO 的由来
=======================

.. code-block:: text

   XLA HLO（内部格式）
       ↓
   MHLO（MLIR HLO，非版本化）
       ↓
   StableHLO（版本化、稳定性保证）
       ↓
   CHLO（自定义 HLO，StableHLO 的超集）

StableHLO 分为两个模块：

- **stablehlo** ：核心稳定操作集（版本化，保证向后兼容）
- **chlo** ：自定义操作（非版本化，包含高级组合操作）

核心操作
================

**算术运算**

.. code-block:: text

   %0 = stablehlo.add %a, %b : tensor<4xf32>
   %1 = stablehlo.multiply %a, %b : tensor<4xf32>
   %2 = stablehlo.dot_general %a, %b {
       dot_dimension_numbers = #stablehlo.dot<
           lhs_batching_dimensions = [0],
           rhs_batching_dimensions = [0],
           lhs_contracting_dimensions = [1],
           rhs_contracting_dimensions = [1]
       >,
       precision_config = [#stablehlo<precision DEFAULT>,
                           #stablehlo<precision DEFAULT>]
   } : (tensor<8x16xf32>, tensor<8x16xf32>) -> tensor<8xf32>

**控制流**

.. code-block:: text

   // 条件执行
   %result = stablehlo.if %pred {
       stablehlo.return %true_val : tensor<f32>
   } else {
       stablehlo.return %false_val : tensor<f32>
   }

   // 循环
   %result = stablehlo.while(%iter = %init) : tensor<4xf32> {
       %cond = "compute_condition"(%iter) : (tensor<4xf32>) -> tensor<i1>
       stablehlo.return %cond : tensor<i1>
   } do {
       %next = "compute_next"(%iter) : (tensor<4xf32>) -> tensor<4xf32>
       stablehlo.return %next : tensor<4xf32>
   }

**通信操作（分布式）**

.. code-block:: text

   // 跨设备 all-reduce
   %result = stablehlo.all_reduce %input
       replica_groups = [[0, 1], [2, 3]]
       {
       ^bb0(%a: f32, %b: f32):
           %sum = stablehlo.add %a, %b : tensor<f32>
           stablehlo.return %sum : tensor<f32>
       } : (tensor<4xf32>) -> tensor<4xf32>

StableHLO 的降级路径
============================

.. code-block:: console

   # StableHLO → 稳定 HLO → linalg → scf → LLVM
   $ stablehlo-translate --deserialize input.mlirbc | \
       mlir-opt \
           --stablehlo-canonicalize \
           --stablehlo-legalize-to-hlo \
           --hlo-legalize-to-linalg \
           --linalg-lower-to-loops \
           --convert-scf-to-cf \
           --convert-arith-to-llvm \
           --convert-func-to-llvm

版本化与序列化
=====================

StableHLO 使用 **MLIR Bytecode** 格式进行序列化：

.. code-block:: console

   # .mlirbc 是 StableHLO 的二进制格式
   $ stablehlo-translate --serialize input.mlir -o model.mlirbc
   $ stablehlo-translate --deserialize model.mlirbc -o output.mlir

版本化保证：

.. code-block:: text

   // 每个 StableHLO 程序都记录了兼容版本
   module attributes {stablehlo.version = #stablehlo<version 0.9.0>} {
       // ...
   }

与 MLIR 生态的关系
======================

StableHLO 是独立仓库，项目地址见 `stablehlo <https://github.com/openxla/stablehlo>`__ ，
不在 ``llvm-project`` 主仓库内。但它遵循 MLIR 的 Dialect 规范，通过
``stablehlo-translate`` 和一系列 MLIR Pass 接入降级管道。

对读者来说，理解 StableHLO 的关键不是记住每个 Op，而是看清它在
渐进降级链路中的位置：

.. mermaid::

   flowchart LR
       A[框架计算图] --> B[StableHLO]
       B --> C[linalg / tensor]
       C --> D[scf / arith]
       D --> E[LLVM Dialect]
       E --> F[LLVM IR]

PyTorch 的 ``torch.compile`` 和 JAX 的 XLA 编译路径，本质上都是把
框架内部的图表示降到这条链路的某一站，再交给 MLIR 管道处理。

CHLO 与 StableHLO 的分工
==============================

``chlo`` （Custom HLO）是 StableHLO 的超集，包含尚未稳定的操作。
典型工作流是：

1. 前端生成 CHLO（可以使用便捷的组合操作）
2. ``--chlo-legalize-to-stablehlo`` 将 CHLO 降为 StableHLO 核心集
3. 后续 Pass 再将 StableHLO 降为 linalg

这种"宽松前端 + 严格核心 + 渐进收紧"的设计，与 MLIR 整体的
渐进降级哲学完全一致。

动手验证
==========

如果你没有安装 ``stablehlo-translate`` ，仍可以用纯 MLIR Dialect
模拟降级管道的后半段。以前文的矩阵乘法为例，在 linalg 层走通
:ref:`mlir-11-06-02` 描述的 tensor → scf 路径，即 StableHLO 降级的
最终落点之一。

.. code-block:: console

   # 验证 MLIR 降级管道（StableHLO 之后的标准路径）
   mlir-opt examples/mlir/chapter_06_lowering/tensor_add.mlir \
       --one-shot-bufferize="bufferize-function-boundaries" \
       --convert-linalg-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts

这条命令展示了：无论前端是 StableHLO、TOSA 还是手写 linalg，
**后半段降级管道是共享的**——这正是 MLIR 框架的价值所在。

本章小结
========

StableHLO 解决了 ML 前端 IR 的 **稳定性和版本化** 问题，但它只是
MLIR 多层降级中的起点。理解它的最好方式，是把它放进
:ref:`mlir-11-06-01` 描述的 Progressive Lowering 全景中，
看清"从计算图到机器码"的完整链路。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
