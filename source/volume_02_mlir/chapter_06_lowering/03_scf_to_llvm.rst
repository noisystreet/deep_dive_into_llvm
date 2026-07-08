.. _mlir-06-06-03:

==============================
scf/arith → LLVM Dialect 降级
==============================

这一阶段将结构化控制流（``scf`` ）和算术运算（``arith`` ）转换为
LLVM Dialect 中的对应操作。这是 MLIR 降级管道中**最标准的阶段**。

.. rst-class:: center

   几乎所有 LLVM 后端的 MLIR 程序都会经过这一步。
   这也是 ``mlir-opt`` 最常测试的降级路径。

scf.for → LLVM
====================

``scf.for`` 被降级为 LLVM 的循环结构（使用 ``llvm.br`` 和 ``llvm.cond_br`` ）：

.. code-block:: text

   // 降级前
   scf.for %i = %c0 to %N step %c1 {
       %v = arith.addi %acc, %i : i32
       scf.yield %v : i32
   }

   // 降级后（cf 形式）
   cf.br ^loop_header(%c0, %init)

   ^loop_header(%i: index, %acc: i32):
       %cond = arith.cmpi slt, %i, %N : index
       cf.cond_br %cond, ^loop_body(%i, %acc), ^loop_exit

   ^loop_body(%i: index, %acc: i32):
       %v = arith.addi %acc, %i : i32
       %next_i = arith.addi %i, %c1 : index
       cf.br ^loop_header(%next_i, %v)

   ^loop_exit:
       // 结果值

这个转换由 ``convert-scf-to-cf`` Pass 处理。

arith → LLVM
====================

标量运算直接映射到 LLVM 指令：

.. list-table:: arith → LLVM 映射
   :header-rows: 1

   * - arith Op
     - LLVM Op
     - C++ 转换实现
   * - ``arith.addi``
     - ``llvm.add``
     - ``rewriter.replaceOpWithNewOp<LLVM::AddOp>``
   * - ``arith.subi``
     - ``llvm.sub``
     - ``rewriter.replaceOpWithNewOp<LLVM::SubOp>``
   * - ``arith.muli``
     - ``llvm.mul``
     - ``rewriter.replaceOpWithNewOp<LLVM::MulOp>``
   * - ``arith.divsi``
     - ``llvm.sdiv``
     - ``rewriter.replaceOpWithNewOp<LLVM::SDivOp>``
   * - ``arith.constant``
     - ``llvm.mlir.constant``
     - ``rewriter.create<LLVM::ConstantOp>``
   * - ``arith.addf``
     - ``llvm.fadd``
     - ``rewriter.replaceOpWithNewOp<LLVM::FAddOp>``
   * - ``arith.cmpi``
     - ``llvm.icmp``
     - ``rewriter.replaceOpWithNewOp<LLVM::ICmpOp>``

由 ``convert-arith-to-llvm`` Pass：

.. code-block:: console

   $ mlir-opt --convert-arith-to-llvm input.mlir

func → LLVM
====================

函数定义和调用也被转换：

.. code-block:: text

   // 降级前
   func.func @add(%a: i32, %b: i32) -> i32 { ... }
   %r = func.call @add(%x, %y) : (i32, i32) -> i32

   // 降级后
   llvm.func @add(%a: i32, %b: i32) -> i32 { ... }
   %r = llvm.call @add(%x, %y) : (i32, i32) -> i32

由 ``convert-func-to-llvm`` Pass：

.. code-block:: console

   $ mlir-opt --convert-func-to-llvm input.mlir

memref → LLVM
====================

``memref`` 是 MLIR 特有的类型。降级时，一个 ``memref<NxMxf32>`` 被分解为
LLVM 的**结构化类型**：

.. code-block:: text

   // memref<4xf32> 在 LLVM Dialect 中表示为：
   !llvm.struct<(
       ptr<f32>,      // 数据指针（allocated）
       ptr<f32>,      // 对齐后的数据指针（aligned）
       i64,           // 偏移量（offset）
       array<1 x i64> // 形状（sizes）
   )>

由 ``convert-memref-to-llvm`` Pass 处理。

完整的降级管道
======================

.. code-block:: console

   # 从 scf/arith/func/memref 到 LLVM Dialect
   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts \
       input.mlir

``--reconcile-unrealized-casts`` 的职责是检查是否还有未消除的
``UnrealizedConversionCastOp``，如果有则报错——这是确保降级完整性的
安全检查。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
