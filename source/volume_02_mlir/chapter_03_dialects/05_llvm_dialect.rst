.. _mlir-03-03-05:

=================
LLVM Dialect
=================

``LLVM`` Dialect 是 MLIR 和 LLVM IR 之间的**桥梁**。它将 LLVM IR 中的指令、
类型和元数据映射为 MLIR 的 Operation 和 Type。

.. rst-class:: center

   如果你想把 MLIR 程序编译为可执行机器码，最终都会经过 ``LLVM`` Dialect——
   它是 MLIR 降级管道中的最后一站。

.. admonition:: LLVM Dialect：为何不直接生成 .ll 文件？
   :class: note

   一个自然的问题是：既然最终要 LLVM IR，为什么不跳过 LLVM Dialect
   直接输出 ``.ll``？答案涉及 **渐进验证** 和 **类型安全**。

   LLVM Dialect 仍是 MLIR 世界的一部分——可以用 MLIR 的 Verifier 检查
   类型一致性，用 Pass 做最后阶段的优化（如 memref 描述符展开）。
   只有确认 LLVM Dialect 模块合法后，``mlir-translate`` 才一次性
   生成 LLVM IR。

   此外，GPU 路径中 NVVM/ROCDL Dialect 也遵循同样模式——先降到
   目标相关的 LLVM 变体 Dialect，再统一翻译。这让 MLIR 能用
   同一套 Translation 框架服务 CPU 和 GPU。

LLVM Dialect 的设计
=========================

``LLVM`` Dialect 的设计原则是：**尽可能地直接映射 LLVM IR**。
每个 LLVM IR 指令在 MLIR 中都有一个对应的 Operation。

.. code-block:: text

   LLVM IR                      MLIR LLVM Dialect
   ─────────────────────────────────────────────
   add i32 %a, %b              llvm.add %a, %b : i32
   load i32, ptr %p            llvm.load %p : !llvm.ptr<i32>
   store i32 %v, ptr %p        llvm.store %v, %p : i32, !llvm.ptr<i32>
   alloca i32, i64 1           llvm.alloca %size x i32
   call i32 @f(i32 %a)         llvm.call @f(%a) : (i32) -> i32

类型映射
================

LLVM Dialect 定义了一组对应于 LLVM IR 类型的 MLIR 类型：

.. code-block:: text

   // 基础类型
   !llvm.i32                    → LLVM IR 中的 i32
   !llvm.ptr<i32>              → LLVM IR 中的 ptr（指向 i32 的指针）
   !llvm.ptr<i8>               → LLVM IR 中的 ptr（指向 i8 的指针）
   !llvm.void                  → LLVM IR 中的 void

   // 复合类型
   !llvm.struct<(i32, ptr<i8>)>  → LLVM IR 中的 { i32, ptr }
   !llvm.array<4 x i32>          → LLVM IR 中的 [4 x i32]
   !llvm.func<i32 (i32, i32)>    → LLVM IR 中的函数类型

在 LLVM 15 之后，LLVM IR 中指针类型变为不透明指针（opaque pointer），
MLIR 的 LLVM Dialect 也做了对应调整：

.. code-block:: text

   // LLVM 14 及之前：类型化指针
   !llvm.ptr<i32>              // i32 指针
   !llvm.ptr<i8>               // i8 指针

   // LLVM 15+：不透明指针
   !llvm.ptr                   // 不透明指针（不携带指向类型信息）

常用 LLVM Operation
=========================

**内存操作**

.. code-block:: text

   // alloca：栈上分配
   %ptr = llvm.alloca %size x i32 : (!llvm.i64) -> !llvm.ptr

   // load：加载
   %val = llvm.load %ptr : !llvm.ptr -> i32

   // store：存储
   llvm.store %val, %ptr : i32, !llvm.ptr

**算术操作**

.. code-block:: text

   %sum = llvm.add %a, %b : i32
   %sub = llvm.sub %a, %b : i32
   %mul = llvm.mul %a, %b : i32

**控制流**

.. code-block:: text

   llvm.br ^bb1
   llvm.cond_br %cond, ^bb1, ^bb2
   llvm.return %val : i32

**函数调用**

.. code-block:: text

   %result = llvm.call @printf(%ptr, %val) : (!llvm.ptr, i32) -> i32

从 MLIR 到 LLVM IR 的翻译
==============================

MLIR 的 LLVM Dialect 到 LLVM IR 的翻译由 ``mlir-translate`` 的
``--mlir-to-llvmir`` 通道完成：

.. code-block:: console

   $ mlir-opt --convert-scf-to-cf --convert-arith-to-llvm \
       --convert-func-to-llvm input.mlir > output_llvm.mlir
   $ mlir-translate --mlir-to-llvmir output_llvm.mlir > output.ll

翻译过程的核心是 ``ModuleTranslation`` 类：

.. code-block:: cpp

   // llvm/lib/Target/LLVMIR/ModuleTranslation.cpp（简化）
   LogicalResult ModuleTranslation::translateModule() {
       for (auto &op : *mlirModule) {
           if (auto funcOp = dyn_cast<llvm::CallOp>(op)) {
               // 将 llvm.call 翻译为 LLVM IR 的 CallInst
               createCall(funcOp);
           }
           // ...
       }
   }

这会生成标准的 LLVM IR，可以被 ``opt`` 和 ``llc`` 继续处理。

LLVM Dialect 与 GPU
==============================

LLVM Dialect 也可以包含 GPU 相关的操作，如 LLVM 内建函数：

.. code-block:: text

   // GPU 线程 ID
   %tid = llvm.intr.nvvm.read.ptx.sreg.tid.x() : i32

   // 同步屏障
   llvm.intr.barrier

在 MLIR-GPU 编译管道中，GPU Dialect 最终也会降级为 LLVM Dialect，
然后通过 LLVM 的后端生成 PTX（NVIDIA）或 AMDGCN（AMD）代码。

源码走读：LLVM Dialect 的 ODS
================================

LLVM Dialect 的操作定义在
`LLVMOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/LLVMIR/LLVMOps.td>`__ 。
设计原则是**一对一映射 LLVM IR**——每个 MLIR 操作都有明确的 LLVM IR 对应物，
这使得 ``mlir-translate`` 的翻译逻辑高度机械化。

类型系统定义在 ``LLVMTypes.td`` 中。LLVM 15 之后引入的不透明指针
（``!llvm.ptr`` ）也在此反映——与第一卷 :ref:`chapter-02-02-instruction-set`
讨论的 LLVM IR 指针演进同步。

源码走读：ModuleTranslation
================================

MLIR → LLVM IR 的翻译由
`ModuleTranslation.cpp <file:///workspace/llvm-project/mlir/lib/Target/LLVMIR/ModuleTranslation.cpp>`__
实现。文件头注释：

.. code-block:: text

   This file implements the translation between an MLIR LLVM dialect module and
   the corresponding LLVMIR module.

翻译器遍历 MLIR Module 中的每个 Operation，通过 ``LLVMTranslationInterface``
分发到具体的翻译函数。生成的 ``llvm::Module`` 可以直接交给 ``opt`` 优化
或 ``llc`` 生成机器码——完整衔接第一卷 :ref:`chapter-09-02-llc` 的工具链。

动手验证
==========

用项目示例走通 MLIR → LLVM Dialect → LLVM IR 的完整链路：

.. code-block:: console

   # 第一步：降级到 LLVM Dialect
   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
       -o /tmp/llvm_dialect.mlir

   # 第二步：翻译为 LLVM IR 文本
   mlir-translate --mlir-to-llvmir /tmp/llvm_dialect.mlir

输出应是标准 LLVM IR 文本，包含 ``define`` 和 ``add`` 指令。
可将此 ``.ll`` 文件继续交给 ``opt -O2`` 或 ``lli`` 执行。

本章小结
========

LLVM Dialect 是 MLIR 与 LLVM 后端之间的精确桥梁。掌握它的关键是理解：
MLIR 降级管道的前半段在各 Dialect 之间转换语义，后半段在 LLVM Dialect 中
固化为一一对应的 LLVM IR 操作，最终由 ``ModuleTranslation`` 导出。

第 3 章 Dialect 概览至此完成。下一章 :ref:`mlir-04-index` 将深入
ODS 如何定义这些 Dialect 中的每一个 Operation 。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
