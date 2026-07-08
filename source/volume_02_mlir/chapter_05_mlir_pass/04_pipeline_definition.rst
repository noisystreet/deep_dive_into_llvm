.. _mlir-05-05-04:

=======================
定义 Pass Pipeline
=======================

Pass Pipeline 是将多个 Pass 组合成一个完整编译流程的方式。
MLIR 提供了灵活的方式来定义、组合和复用的 Pipeline。

.. rst-class:: center

   Pipeline = 一系列 Pass 的有序组合。每个 Pass 接收 IR，转换后
   传递给下一个 Pass。

创建 Pipeline
===================

**简单的 Pipeline**

.. code-block:: cpp

   PassManager pm(ctx);
   pm.addPass(createCanonicalizerPass());
   pm.addPass(createCSEPass());
   pm.addPass(createMyOptPass());

   if (failed(pm.run(module))) {
       llvm::errs() << "Pipeline failed!\n";
       return 1;
   }

**嵌套 Pipeline（在特定 Operation 上运行）**

.. code-block:: cpp

   // 先运行顶层 Pass
   pm.addPass(createMyModulePass());

   // 然后对每个 FuncOp 运行嵌套 Pass
   OpPassManager &funcPM = pm.nest<FuncOp>();
   funcPM.addPass(createCanonicalizerPass());
   funcPM.addPass(createMyFuncOptPass());

   // 再对 scf.for 操作运行嵌套 Pass
   OpPassManager &loopPM = pm.nest<scf::ForOp>();
   loopPM.addPass(createLoopOptPass());

**复杂嵌套结构**

.. code-block:: cpp

   // builtin.module → (func, scf.for)
   //                 func → (canonicalize, cse)
   //                 scf.for → (loop-opt)
   pm.nest<FuncOp>().addPass(createCanonicalizerPass());
   pm.nest<FuncOp>().addPass(createCSEPass());
   pm.nest<scf::ForOp>().addPass(createLoopOptPass());

mlir-opt 命令行
=====================

``mlir-opt`` 是测试和调试 Pipeline 的主要工具：

.. code-block:: console

   # 运行完整的 Pipeline
   $ mlir-opt --canonicalize --cse --my-opt input.mlir

   # 使用 --pass-pipeline 参数
   $ mlir-opt --pass-pipeline="builtin.module(canonicalize,cse,my-opt)" input.mlir

   # 保存中间结果
   $ mlir-opt --canonicalize --cse --mlir-print-ir-after-all input.mlir

   # 在指定 Pass 后停止
   $ mlir-opt --canonicalize --cse --mlir-print-ir-before=cse input.mlir

MLIR 内置的常用 Pass
============================

.. list-table:: 常用内置 Pass
   :header-rows: 1

   * - Pass 名称
     - 功能
     - 适用场景
   * - ``canonicalize``
     - 应用所有 Canonicalization 模式
     - 任何 Pipeline 的"热身"步骤
   * - ``cse``
     - 公共子表达式消除
     - 减少重复计算
   * - ``inline``
     - 函数内联
     - 减少函数调用开销
   * - ``symbol-dce``
     - 删除死函数和全局变量
     - 清理 IR
   * - ``sccp``
     - 稀疏条件常量传播
     - 常量折叠
   * - ``convert-scf-to-cf``
     - 结构化循环 → 底层分支
     - 降级到 LLVM 前
   * - ``convert-arith-to-llvm``
     - arith → LLVM Dialect
     - LLVM 代码生成
   * - ``convert-func-to-llvm``
     - func → LLVM Dialect
     - LLVM 代码生成

注册自定义 Pipeline
===========================

**ODS 定义**

.. code-block:: text

   // MyPipelines.td
   def MyPipeline : PassPipeline<"my-pipeline"> {
       let summary = "Custom optimization pipeline";
       let description = [{
           A custom pipeline consisting of canonicalization,
           CSE, and my custom optimization pass.
       }];
   }

**C++ 实现**

.. code-block:: cpp

   void registerMyPipeline() {
       PassPipelineRegistration<>("my-pipeline",
           "Custom optimization pipeline",
           [](OpPassManager &pm) {
               pm.addPass(createCanonicalizerPass());
               pm.addPass(createCSEPass());
               pm.addPass(createMyOptPass());

               // 嵌套 Pass
               pm.nest<FuncOp>().addPass(createFuncOptPass());
           });
   }

**使用时**

.. code-block:: console

   $ mlir-opt --my-pipeline input.mlir

或者：

.. code-block:: cpp

   pm.addPass(parsePassPipeline("my-pipeline"));

完整示例：MLIR → LLVM 的降级 Pipeline
================================================

.. code-block:: cpp

   void buildMLIRToLLVMPipeline(OpPassManager &pm) {
       // 第一步：高层优化
       pm.addPass(createCanonicalizerPass());
       pm.addPass(createCSEPass());

       // 第二步：tensor → memref（Bufferization）
       pm.addPass(createOneShotBufferizePass());

       // 第三步：结构化控制流 → 底层分支
       pm.addPass(createConvertSCFToCFPass());

       // 第四步：Dialect 转换（arith, func, memref → LLVM）
       pm.addPass(createConvertArithToLLVMPass());
       pm.addPass(createConvertFuncToLLVMPass());
       pm.addPass(createConvertMemRefToLLVMPass());

       // 第五步：最终清理
       pm.addPass(createCanonicalizerPass());

       // 第六步：LLVM 级别优化
       pm.addPass(createLLVMOptimizationPass());
   }

   // 使用
   PassManager pm(ctx);
   buildMLIRToLLVMPipeline(pm);
   if (failed(pm.run(module))) {
       return failure();
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
