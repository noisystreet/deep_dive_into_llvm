.. _mlir-11-06-04:

======================
LLVM Dialect → LLVM IR
======================

这是 MLIR 降级管道的 **最后一步**——将 LLVM Dialect 翻译为标准的 LLVM IR。
这一步由 ``mlir-translate`` 完成。

.. rst-class:: center

   MLIR 管道的终点——从此以后，交由 LLVM ``opt`` 和 ``llc`` 接管。

.. admonition:: MLIR 与 LLVM 的"主权交接"
   :class: note

   ``mlir-translate --mlir-to-llvmir`` 是 MLIR 世界的最后一道门。
   出门之后， ``opt -O2`` 、 ``llc`` 、 ``lli`` 完全沿用第一卷的工具链——
   寄存器分配、指令选择、ELF 生成，MLIR 不再介入。

   这意味着 MLIR 不必重复实现后端——它专注于"如何把领域知识
   翻译成 LLVM 能理解的 IR"。对读者来说，掌握 MLIR 降级的终点，
   就是掌握 LLVM 优化的起点：把 ``mlir-translate`` 的输出
   喂给 ``opt`` ，就能用第一卷学到的 Pass 继续优化。

Translation 接口
========================

MLIR 的 Translation 框架定义了从 MLIR Operation 到 LLVM IR 的映射。
核心类是 ``ModuleTranslation`` ：

.. code-block:: cpp

   // llvm/lib/Target/LLVMIR/ModuleTranslation.cpp
   // ModuleTranslation 负责将 MLIR ModuleOp 翻译为 llvm::Module

   LogicalResult ModuleTranslation::translateModule() {
       // 1. 遍历 ModuleOp 中的所有 Operation
       for (auto &op : *mlirModule) {
           if (auto funcOp = dyn_cast<llvm::FuncOp>(op)) {
               // 2. 将 llvm.func 翻译为 LLVM IR 中的 Function
               translateFunction(funcOp);
           } else if (auto globalOp = dyn_cast<llvm::GlobalOp>(op)) {
               // 3. 将 llvm.global 翻译为 LLVM IR 中的 GlobalVariable
               translateGlobal(globalOp);
           }
       }
       return success();
   }

Operation 映射表
========================

以下是一些关键 Operation 的翻译映射：

.. list-table:: LLVM Dialect → LLVM IR 映射
   :header-rows: 1

   * - MLIR Operation
     - LLVM IR 指令
     - MLIR 操作数 → LLVM 操作数
   * - ``llvm.add``
     - ``add``
     - 直接映射
   * - ``llvm.load``
     - ``load``
     - 地址映射
   * - ``llvm.store``
     - ``store``
     - 值和地址映射
   * - ``llvm.alloca``
     - ``alloca``
     - 大小和类型映射
   * - ``llvm.call``
     - ``call``
     - 函数名和参数映射
   * - ``llvm.br``
     - ``br``
     - 目标 Label 映射
   * - ``llvm.cond_br``
     - ``br i1``
     - 条件和 Label 映射
   * - ``llvm.return``
     - ``ret``
     - 返回值映射

运行 Translation
========================

.. code-block:: console

   # 最简单的用法
   $ mlir-translate --mlir-to-llvmir input_llvm_dialect.mlir

   # 完整的端到端管道
   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       input.mlir \
       | mlir-translate --mlir-to-llvmir -o output.ll

   # 继续用 LLVM 工具链处理
   $ opt -O2 output.ll -o output_opt.ll
   $ llc -filetype=obj output_opt.ll -o output.o
   $ clang output.o -o executable

mlir-cpu-runner
========================

``mlir-cpu-runner`` 是一个便捷工具，直接运行 MLIR 程序的 JIT 编译结果：

.. code-block:: console

   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts \
       input.mlir \
       | mlir-cpu-runner -e main -entry-point-result=i32

它内部调用了：
1. ``mlir-translate --mlir-to-llvmir`` 生成 LLVM IR
2. LLVM ORC JIT 编译为机器码
3. 执行并返回结果

端到端示例
================

.. code-block:: text

   // add.mlir
   func.func @main() -> i32 {
       %0 = arith.constant 40 : i32
       %1 = arith.constant 2 : i32
       %2 = arith.addi %0, %1 : i32
       func.return %2 : i32
   }

.. code-block:: console

   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       add.mlir \
       | mlir-cpu-runner -e main -entry-point-result=i32

   // 输出：42

源码走读：ModuleTranslation 的翻译流程
======================================

前文示例代码的路径需要更正——实际实现位于
`ModuleTranslation.cpp <file:///workspace/llvm-project/mlir/lib/Target/LLVMIR/ModuleTranslation.cpp>`__ ，
而非 ``llvm/lib/Target/`` 。

文件头注释明确了职责：

.. code-block:: text

   This file implements the translation between an MLIR LLVM dialect module and
   the corresponding LLVMIR module.

翻译器的工作方式是 **逐 Operation 分发** ：对每个 ``llvm.func`` 内的
``llvm.add`` 、 ``llvm.load`` 等操作，调用对应的 ``LLVMTranslationInterface``
生成 ``llvm::Instruction`` 。类型映射由 ``TypeToLLVM.h`` 统一处理，
确保 ``!llvm.ptr`` 等 MLIR 类型正确转为 LLVM IR 类型。

这与 :ref:`chapter-09-04-llvm-dis-and-asm` 讨论的 LLVM bitcode/IR 文本
形成闭环：MLIR 管道产出标准 ``.ll`` 文件后，后续工具链与第一卷完全一致。

动手验证
==========

用项目示例走通 MLIR → LLVM IR → 优化的完整链路：

.. code-block:: console

   # 降级到 LLVM Dialect
   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
       -o /tmp/llvm_dialect.mlir

   # 翻译为 LLVM IR
   mlir-translate --mlir-to-llvmir /tmp/llvm_dialect.mlir -o /tmp/output.ll

   # 用 LLVM opt 优化（第一卷工具链）
   opt -O2 -S /tmp/output.ll

对比 ``opt`` 前后的 IR，观察 ``add`` 指令是否被保留或进一步优化。

本章小结
========

LLVM Dialect → LLVM IR 是 MLIR 管道的终点站。 ``mlir-translate`` 完成最后
的格式转换，之后 ``opt`` 、 ``llc`` 、 ``lli`` 接管——MLIR 与 LLVM 的边界
就在这一步。第 6 章降级管道至此完整闭环。


.. rubric:: 进一步阅读

- `Bufferization 文档 <https://mlir.llvm.org/docs/Bufferization/>`_ — One-Shot Bufferization
- `LLVM Translation <https://mlir.llvm.org/docs/TargetLLVM/>`_ — MLIR → LLVM IR 翻译
- :ref:`第 1 卷 LLVM IR 基础 <chapter-02-01-ir-basics>` — LLVM IR 语法回顾
