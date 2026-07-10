.. _mlir-11-06-03:

==============================
scf/arith → LLVM Dialect 降级
==============================

这一阶段将结构化控制流（ ``scf`` ）和算术运算（ ``arith`` ）转换为
LLVM Dialect 中的对应操作。这是 MLIR 降级管道中 **最标准的阶段** 。

.. rst-class:: center

   几乎所有 LLVM 后端的 MLIR 程序都会经过这一步。
   这也是 ``mlir-opt`` 最常测试的降级路径。

.. admonition:: 三步 Conversion：scf → arith → func → llvm
   :class: tip

   这一阶段看似三个独立 Pass，实则环环相扣：

   1. **scf → cf** — 循环展平为 CFG， ``iter_args`` 变成 Block 参数
   2. **arith → llvm** — 整数运算映射为 ``llvm.add`` 等指令
   3. **func → llvm** — 函数签名和 ``return`` 映射为 ``llvm.func``

   顺序不能乱：先拆控制流，再换算术指令，最后统一函数 ABI。
   项目 CI 脚本 ``verify-mlir-examples.sh`` 就是按这个顺序
   验证 ``vector_add.mlir`` 的——它是整个 MLIR 管道的"冒烟测试"。

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
LLVM 的 **结构化类型** ：

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
``UnrealizedConversionCastOp`` ，如果有则报错——这是确保降级完整性的
安全检查。

源码走读：scf.for 如何变成 CFG
======================================

``--convert-scf-to-cf`` 的实现位于
`SCFToControlFlow.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/SCFToControlFlow/SCFToControlFlow.cpp>`__。

这个文件最值得读的不是某个函数，而是第 43–61 行的 **设计注释** 。
它用 ASCII 图描述了 ``scf.for`` 降级后的 CFG 结构，并维护三个不变量：

1. 生成的 CFG 子图有 **单一入口** 和 **单一出口**
2. 入口块是父 Region 的第一个块，出口块是最后一个块
3. 循环携带值通过条件块的参数在所有块中可见

理解了这段注释，就能明白为什么降级后的 ``cf.cond_br`` 需要携带
``(%iv, %init...)`` 这样的参数列表——它们就是原来 ``scf.for`` 的
归纳变量和 ``iter_args`` 。

这与第一卷 :ref:`chapter-02-03-module-function-basicblock` 讨论的
LLVM IR 基本块和 PHI 节点有异曲同工之妙：MLIR 用 Region 保留了结构化信息，
降级时才展开为显式 CFG。

源码走读：arith → LLVM 的模式匹配
======================================

``--convert-arith-to-llvm`` 由
`ArithToLLVM.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/ArithToLLVM/ArithToLLVM.cpp>`__
实现。它的核心是一组 **Pattern**——每个 Pattern 匹配一个 ``arith`` 操作，
替换为对应的 ``llvm`` 操作。

以 ``arith.addi`` 为例，转换逻辑大致为：

.. code-block:: cpp

   rewriter.replaceOpWithNewOp<LLVM::AddOp>(op, adaptor.getOperands());

标量算术几乎是 1:1 映射，但向量版本的 ``arith.addf`` 需要处理
LLVM 向量类型和 rounding mode 属性——文件中 ``ConstrainedVectorConvertToLLVMPattern``
模板就是为此存在的。

这种"一个 Pattern 管一种 Op"的组织方式，与 :ref:`mlir-11-05-02` 讨论的
Pattern Rewrite 框架完全一致。

func 与 memref 的降级要点
==============================

**func → llvm** ：`FuncToLLVM.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/FuncToLLVM/FuncToLLVM.cpp>`__
将 ``func.func`` 转为 ``llvm.func`` ，调用约定由 ``LLVMConversionTarget`` 统一管理。

**memref → llvm** ： ``memref`` 在 LLVM Dialect 中被表示为描述符结构体
（指针 + 对齐指针 + offset + sizes），而非裸指针。
这让 MLIR 在降级过程中保留了对齐、偏移和形状信息，到 LLVM IR 时才进一步展开。

动手验证
==========

用项目示例走一遍完整降级：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts

预期输出：

.. code-block:: text

   llvm.func @add(%arg0: i32, %arg1: i32) -> i32 {
     %0 = llvm.add %arg0, %arg1 : i32
     llvm.return %0 : i32
   }

若要 JIT 执行，可接上 ``mlir-cpu-runner`` ，详见 :ref:`mlir-11-11-04` 。

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-cpu-runner -entry-point-result=i32 -e add 3 5

本章小结
========

scf/arith → LLVM Dialect 是 MLIR 降级管道中 **最成熟** 的一段。
scf 展开为 CFG，arith 映射为 LLVM 指令，func/memref 处理函数边界和内存描述符。
全部完成后，模块中只剩 LLVM Dialect 的操作，可以交给
:ref:`mlir-11-06-04` 描述的 ``ModuleTranslation`` 导出为 LLVM IR。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
