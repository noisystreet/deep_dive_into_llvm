.. _mlir-06-06-04:

======================
LLVM Dialect → LLVM IR
======================

这是 MLIR 降级管道的**最后一步**——将 LLVM Dialect 翻译为标准的 LLVM IR。
这一步由 ``mlir-translate`` 完成。

.. rst-class:: center

   MLIR 管道的终点——从此以后，交由 LLVM ``opt`` 和 ``llc`` 接管。

Translation 接口
========================

MLIR 的 Translation 框架定义了从 MLIR Operation 到 LLVM IR 的映射。
核心类是 ``ModuleTranslation``：

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
