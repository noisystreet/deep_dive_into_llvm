.. _mlir-07-07-02:

=================
StableHLO Dialect
=================

StableHLO 是 MLIR 生态中**最重要的机器学习 Dialect** 之一。它是
HLO（High-Level Operations）的稳定版本，被 TensorFlow、JAX 和 PyTorch
等框架用于表示计算图。

.. rst-class:: center

   StableHLO = HLO 的稳定演进版。它在保持向后兼容的同时提供版本化升级路径。

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

- **stablehlo**：核心稳定操作集（版本化，保证向后兼容）
- **chlo**：自定义操作（非版本化，包含高级组合操作）

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
