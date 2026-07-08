.. _mlir-03-03-05:

=================
LLVM Dialect
=================

``LLVM`` Dialect 是 MLIR 和 LLVM IR 之间的**桥梁**。它将 LLVM IR 中的指令、
类型和元数据映射为 MLIR 的 Operation 和 Type。

.. rst-class:: center

   如果你想把 MLIR 程序编译为可执行机器码，最终都会经过 ``LLVM`` Dialect——
   它是 MLIR 降级管道中的最后一站。

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
