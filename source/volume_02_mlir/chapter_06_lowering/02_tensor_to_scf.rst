.. _mlir-06-06-02:

=================
tensor → scf 降级
=================

从 ``tensor`` / ``linalg`` 到 ``scf`` / ``arith`` 的降级是 MLIR 计算
降级管道中的第一步。它将高层**张量计算**展开为显式的**标量循环**。

.. rst-class:: center

   tensor 是"值"，scf 是"控制流"。降级 tensor → scf 的本质是把
   隐式的张量计算转换为显式的循环计算。

Bufferization：tensor → memref
=====================================

Bufferization 是 tensor 计算降级的第一步。它将不可变的 ``tensor`` 值
转换为可变的 ``memref`` （内存引用）。

**降级前（tensor 形式）**

.. code-block:: text

   func.func @add(%a: tensor<4xf32>, %b: tensor<4xf32>) ->
       tensor<4xf32> {
       %0 = linalg.add %a, %b : tensor<4xf32>
       func.return %0 : tensor<4xf32>
   }

**降级后（memref 形式）**

.. code-block:: text

   func.func @add(%a: memref<4xf32>, %b: memref<4xf32>,
                  %out: memref<4xf32>) {
       linalg.add ins(%a, %b : memref<4xf32>, memref<4xf32>)
           outs(%out : memref<4xf32>)
       func.return
   }

由 ``one-shot-bufferize`` Pass 完成：

.. code-block:: console

   $ mlir-opt --one-shot-bufferize input.mlir

One-Shot Bufferize 的核心策略是**就地缓冲** （in-place bufferization）。
它分析 tensor 的使用链，尽可能复用现有的缓冲区，避免内存分配。

**Bufferization 的主要挑战**：

- **别名分析**：判断两个 memref 是否指向同一内存区域
- **就地更新判断**：确认可以就地修改而不影响其他使用者
- **内存分配边界**：在无法就地更新时插入分配

linalg.generic 到 scf.for 的降级
====================================

**降级前（linalg.generic）**

.. code-block:: text

   %result = linalg.generic {
       indexing_maps = [
           affine_map<(i) -> (i)>,
           affine_map<(i) -> (i)>
       ],
       iterator_types = ["parallel"]
   } ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
     outs(%out : tensor<4xf32>) {
   ^bb0(%x: f32, %y: f32, %z: f32):
       %sum = arith.addf %x, %y : f32
       linalg.yield %sum : f32
   } -> tensor<4xf32>

**降级后（scf.for）**

.. code-block:: text

   %result = scf.for %i = %c0 to %c4 step %c1
       iter_args(%acc = %out) -> tensor<4xf32> {
       %a_elem = tensor.extract %a[%i] : tensor<4xf32>
       %b_elem = tensor.extract %b[%i] : tensor<4xf32>
       %sum = arith.addf %a_elem, %b_elem : f32
       %new = tensor.insert %sum into %acc[%i] : tensor<4xf32>
       scf.yield %new : tensor<4xf32>
   }

这个过程由 ``linalg-lower-to-loops`` Pass 完成。

矩阵乘法的展开
========================

矩阵乘法降级为三重嵌套循环：

.. code-block:: text

   %C = linalg.matmul ins(%A, %B : tensor<4x4xf32>, tensor<4x4xf32>)
       outs(%C_init : tensor<4x4xf32>) -> tensor<4x4xf32>

   // 降级后：
   scf.for %i = %c0 to %c4 step %c1 {
       scf.for %j = %c0 to %c4 step %c1 {
           scf.for %k = %c0 to %c4 step %c1 {
               %a = tensor.extract %A[%i, %k] : tensor<4x4xf32>
               %b = tensor.extract %B[%k, %j] : tensor<4x4xf32>
               %c = tensor.extract %C[%i, %j] : tensor<4x4xf32>
               %mul = arith.mulf %a, %b : f32
               %sum = arith.addf %c, %mul : f32
               %new = tensor.insert %sum into %C[%i, %j] : tensor<4x4xf32>
           }
       }
   }

降级管道示例
==================

.. code-block:: console

   $ mlir-opt \
       --linalg-generalize-named-ops \
       --linalg-lower-to-loops \
       --one-shot-bufferize \
       input.mlir

降级顺序很重要——先展开命名操作（如 ``linalg.matmul`` → ``linalg.generic`` ），
然后将通用操作降级为循环。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
