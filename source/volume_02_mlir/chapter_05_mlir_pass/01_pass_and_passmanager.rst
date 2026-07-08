.. _mlir-05-05-01:

=========================
Pass 与 PassManager
=========================

MLIR 的 Pass 框架提供了在 IR 上进行**模块化分析和转换**的能力。
与 LLVM Pass 框架类似，MLIR 的 Pass 也运行在 IR 之上，但两者在
设计上有显著区别。

.. rst-class:: center

   MLIR 的 Pass 框架是**多层级**的——同一个 Pipeline 可以同时操作
   多个 Dialect 的 Operation。

.. admonition:: 为什么 MLIR 要"重新发明" Pass 框架？
   :class: note

   LLVM 已经有了一套成熟的 Pass 框架，为什么 MLIR 还要重新写一套？
   
   原因在于**多级 IR 的特性要求多级 Pass 管理**。LLVM 只有一种 IR，
   所以它的 PassManager 只需要管理"一个 IR 上的 Pass 顺序"。
   而 MLIR 的 Pass 需要同时管理：

   1. **不同 Dialect 之间的降级 Pass** （如 ``convert-scf-to-cf`` ）
   2. **同一个 Dialect 内的优化 Pass** （如 ``canonicalize`` ）
   3. **跨 Dialect 的分析 Pass** （如检测 linalg 和 scf 之间的数据流）

   想象一下，你要在一个 Pipeline 中同时运行：
   ``canonicalize (all dialects) → convert-scf-to-cf → arith-optimize → convert-to-llvm``

   MLIR 的 PassManager 需要能在不同的 IR 层级之间切换——这在 LLVM 的
   Pass 框架中是做不到的（因为 LLVM 的 Pass 操作的都是同一种 IR）。

   更关键的是，MLIR 的 Pass 框架支持**嵌套 PassManager**——可以在
   特定 Operation 的 Region 内单独运行 Pass。例如，可以先在函数级别
   运行 ``cse``，然后在循环级别运行 ``loop-unroll``，再回到函数级别
   运行 ``inline``。这种"聚焦式"的 Pass 管理是 MLIR 独有的能力。

Pass 类型
===============

MLIR 提供两种类型的 Pass：**Operation Pass** 和 **Analysis Pass**。

**Operation Pass**

Operation Pass 是最常用的 Pass 类型。它遍历 IR 中的 Operation 并执行转换。

.. code-block:: cpp

   // 继承 OpRewritePattern 的模式匹配 Pass
   struct MyPattern : public OpRewritePattern<MyOp> {
       LogicalResult matchAndRewrite(MyOp op,
           PatternRewriter &rewriter) const override {
           // 重写逻辑
           return success();
       }
   };

   // 或者继承 Pass 类
   struct MyPass : public PassWrapper<MyPass, OperationPass<FuncOp>> {
       void runOnOperation() override {
           FuncOp func = getOperation();
           // 处理函数
       }
   };

**Analysis Pass**

Analysis Pass 只分析 IR，不修改：

.. code-block:: cpp

   struct MyAnalysis {
       MyAnalysis(Operation *op) {
           // 分析逻辑
       }
   };

   // 在其他 Pass 中使用分析结果
   void runOnOperation() override {
       auto &analysis = getAnalysis<MyAnalysis>();
   }

Pass 的注册
=================

**ODS 声明式注册**

.. code-block:: text

   // MyPasses.td
   def MyOptPass : Pass<"my-opt"> {
       let summary = "My optimization pass";
       let description = [{
           Performs a custom optimization on the IR.
       }];

       // 可选的参数
       let options = [
           Option<"enable", "enable", "bool",
               "Enable the optimization", "false">,
           Option<"threshold", "threshold", "int",
               "Threshold value", "10">
       ];

       // 可选的统计信息
       let statistics = [
           Statistic<"numOpt", "num-opt",
               "Number of optimizations performed">
       ];

       // Pass 的依赖
       let dependentDialects = [
           "arith::ArithDialect",
           "scf::SCFDialect"
       ];
   }

**生成 C++ 代码**

.. code-block:: console

   $ mlir-tblgen -gen-pass-decls MyPasses.td -o MyPasses.h.inc

**注册 Pass**

.. code-block:: cpp

   // 在库初始化时注册
   void registerMyPasses() {
       PassRegistration<MyOptPass>();
   }

PassManager 的使用
=========================

PassManager 是 Pass 的执行容器。它管理 Pass 的执行顺序和依赖关系。

**基本使用**

.. code-block:: cpp

   // 创建 PassManager
   PassManager pm(ctx);

   // 添加 Pass
   pm.addPass(std::make_unique<MyOptPass>());
   pm.addPass(std::make_unique<AnotherPass>());

   // 在 ModuleOp 上运行
   if (failed(pm.run(module))) {
       module.emitError("Pass pipeline failed");
       return failure();
   }

**嵌套 PassManager**

MLIR 支持在特定 Operation 上运行 Pass：

.. code-block:: cpp

   // 在 FuncOp 上运行
   pm.addPass(createCanonicalizerPass());

   // 在 scf::ForOp 上运行
   pm.nest<scf::ForOp>().addPass(createLoopOptPass());

**Pass Pipeline 的字符串形式**

.. code-block:: cpp

   // 通过字符串指定 Pipeline
   pm.addPass(parsePassPipeline("builtin.module(my-opt,canonicalize)"));

   // 也可以通过命令行
   // mlir-opt --pass-pipeline="builtin.module(my-opt,canonicalize)" input.mlir

Pass 的统计和调试
======================

**统计信息（Statistics）**

.. code-block:: cpp

   struct MyPass : public PassWrapper<MyPass, OperationPass<FuncOp>> {
       // ODS 中定义的统计项
       Statistic numOpt{this, "num-opt",
           "Number of optimizations performed"};

       void runOnOperation() override {
           numOpt++;
       }
   };

**IR Dump**

.. code-block:: console

   # 在 Pass 前后打印 IR
   $ mlir-opt --my-opt --debug-only=my-opt input.mlir

   # 开启详细的 Pass 日志
   $ mlir-opt --my-opt --pass-pipeline-crash-reproducer input.mlir

**验证（Verifier）**

PassManager 会在每个 Pass 之后自动运行验证器。如果 IR 不合法，
会立即报错。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
