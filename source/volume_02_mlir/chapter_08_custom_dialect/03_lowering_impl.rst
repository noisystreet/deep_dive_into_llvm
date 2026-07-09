.. _mlir-08-08-03:

==========================
实现 Lowering 到 arith/scf
==========================

定义完 Operation 后，下一步是编写**降级模式** （Conversion Pattern），
将 MyDSL 的 Operator 转换为 MLIR 标准 Dialect 的操作。

.. rst-class:: center

   "写降级模式"是自定义 Dialect 开发中最核心的工程任务。

.. admonition:: Partial Conversion：只降你想降的部分
   :class: note

   自定义 Dialect 降级很少一步完成。``DialectConversion`` 支持
   **Partial Conversion**——只转换目标 Dialect 的 Op，其余保持不变。

   典型策略：MyDSL → arith/scf（第一层）→ llvm（第二层）。
   每层用独立的 ``ConversionTarget`` 声明"哪些 Op 是合法的"。
   如果降级后仍残留 MyDSL Op，说明 Pattern 覆盖不完整——
   ``mlir-opt`` 会打印具体哪个 Op 无法转换，这是最有效的调试线索。

   Toy Ch6 的 ``LowerToAffine`` 和 ``LowerToLLVM`` 就是分两层降级的经典范例。

降级目标
==================

.. code-block:: text

   my_dsl.mac %a, %b, %c : i32
       ↓
   %mul = arith.muli %a, %b : i32
   %add = arith.addi %mul, %c : i32

   my_dsl.square %x : i32
       ↓
   arith.muli %x, %x : i32

降级 Pattern 实现
========================

**MacOp 降级**

.. code-block:: cpp

   // MyDSLToArith.cpp
   #include "mydsl/MyDSLOps.h"
   #include "mlir/IR/PatternMatch.h"
   #include "mlir/Dialect/Arith/IR/Arith.h"

   struct MacOpLowering : public OpRewritePattern<MacOp> {
       MacOpLowering(MLIRContext *context)
           : OpRewritePattern<MacOp>(context) {}

       LogicalResult matchAndRewrite(MacOp op,
           PatternRewriter &rewriter) const override {

           // 获取位置
           Location loc = op.getLoc();

           // 创建乘法
           Value mul = rewriter.create<arith::MulIOp>(
               loc, op.getA(), op.getB());

           // 创建加法
           Value add = rewriter.create<arith::AddIOp>(
               loc, mul, op.getC());

           // 用结果替换原 op
           rewriter.replaceOp(op, add);
           return success();
       }
   };

**SquareOp 降级**

.. code-block:: cpp

   struct SquareOpLowering : public OpRewritePattern<SquareOp> {
       SquareOpLowering(MLIRContext *context)
           : OpRewritePattern<SquareOp>(context) {}

       LogicalResult matchAndRewrite(SquareOp op,
           PatternRewriter &rewriter) const override {

           Location loc = op.getLoc();

           // 平方 = 自乘
           Value mul = rewriter.create<arith::MulIOp>(
               loc, op.getX(), op.getX());

           rewriter.replaceOp(op, mul);
           return success();
       }
   };

注册降级 Pattern
========================

.. code-block:: cpp

   // 将 pattern 注册到 Dialect
   void MyDSLDialect::getCanonicalizationPatterns(
       RewritePatternSet &results) const {
       results.add<MacOpLowering, SquareOpLowering>(getContext());
   }

或者作为一个独立的降级 Pass：

.. code-block:: cpp

   struct ConvertMyDSLToArithPass
       : public PassWrapper<ConvertMyDSLToArithPass,
                            OperationPass<FuncOp>> {

       void runOnOperation() override {
           RewritePatternSet patterns(&getContext());
           patterns.add<MacOpLowering, SquareOpLowering>(&getContext());

           // 使用贪心模式应用
           if (failed(applyPatternsAndFoldGreedily(
                   getOperation(), std::move(patterns)))) {
               signalPassFailure();
           }
       }
   };

完整的降级管道
==================

将 MyDSL 降级到可执行代码的完整路径：

.. code-block:: console

   $ mlir-opt \
       --convert-mydsl-to-arith \    # MyDSL → arith（自定义）
       --convert-arith-to-llvm \     # arith → LLVM
       --convert-func-to-llvm \      # func → LLVM
       test.mlir | mlir-translate --mlir-to-llvmir

降级前 vs 降级后
========================

.. code-block:: text

   // === 降级前（MyDSL）===
   func.func @test(%a: i32, %b: i32) -> i32 {
       %0 = my_dsl.mac %a, %b, %a : i32
       %1 = my_dsl.square %0 : i32
       func.return %1 : i32
   }

   // === 降级后（arith）===
   func.func @test(%a: i32, %b: i32) -> i32 {
       %0 = arith.muli %a, %b : i32
       %1 = arith.addi %0, %a : i32
       %2 = arith.muli %1, %1 : i32
       func.return %2 : i32
   }

   // === 进一步降级到 LLVM IR ===
   define i32 @test(i32 %a, i32 %b) {
       %0 = mul i32 %a, %b
       %1 = add i32 %0, %a
       %2 = mul i32 %1, %1
       ret i32 %2
   }

验证降级正确性
==================

使用 ``mlir-opt`` 和 ``FileCheck`` 进行测试：

.. code-block:: text

   // CHECK: arith.muli
   // CHECK: arith.addi
   // CHECK: arith.muli
   func.func @test(%a: i32, %b: i32) -> i32 {
       %0 = my_dsl.mac %a, %b, %a : i32
       %1 = my_dsl.square %0 : i32
       func.return %1 : i32
   }

与 Toy Tutorial 的降级对照
================================

MyDSL 的 ``OpRewritePattern`` 写法与 Toy Ch6 的 ``OpConversionPattern`` 一脉相承。
Toy 的 ``PrintOpLowering`` 定义在
`LowerToLLVM.cpp <file:///workspace/llvm-project/mlir/examples/toy/Ch6/mlir/LowerToLLVM.cpp>`__ ：

.. code-block:: text

   // Toy 文件头注释描述了完整降级链路：
   // Arithmetic + Func --> LLVM (Dialect)
   // 'toy.print' --> Loop (SCF) --> printf

Toy 使用 ``OpConversionPattern`` 而非 ``OpRewritePattern`` ，因为它走的是
**Dialect Conversion** 框架 （:ref:`mlir-05-05-03`），需要配合 ``TypeConverter``
处理类型变化。MyDSL 在同一类型内降级到 arith，用更轻量的 RewritePattern 即可。

Toy Ch6 的 ``ToyToLLVMLoweringPass`` 展示了完整管道的注册方式：

.. code-block:: cpp

   target.addLegalDialect<LLVM::LLVMDialect>();
   target.addIllegalDialect<arith::ArithDialect, func::FuncDialect>();
   // ... populate patterns ...
   if (failed(applyFullConversion(module, target, std::move(patterns))))
       signalPassFailure();

这与前文 MyDSL 的 ``applyPatternsAndFoldGreedily`` 形成对比：
- **Greedy Rewrite** — 同类型替换，适合 MyDSL → arith
- **Full Conversion** — 跨 Dialect 类型转换，适合 arith → LLVM

源码走读：GreedyPatternRewriteDriver
======================================

``applyPatternsAndFoldGreedily`` 的实现在
`GreedyPatternRewriteDriver.cpp <file:///workspace/llvm-project/mlir/lib/Transforms/Utils/GreedyPatternRewriteDriver.cpp>`__ 。
它反复遍历 IR，对每个 Operation 尝试匹配已注册的 Pattern，直到不动点。

MyDSL 的 ``MacOpLowering::matchAndRewrite`` 遵循标准三步：

1. ``rewriter.create`` 创建替换 Operation
2. ``rewriter.replaceOp`` 用新结果替换旧 Op
3. ``return success()`` 告知 driver 匹配成功

动手验证
==========

用项目示例模拟 MyDSL 降级后的 arith 管道：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-translate --mlir-to-llvmir

输出应包含 ``define i32 @add`` 和 ``add i32`` 指令——
这正是 MyDSL 完整降级链路的最终落点。

本章小结
========

降级 Pattern 是自定义 Dialect 的核心工程产物。MyDSL 用 RewritePattern 降到 arith，
后续管道与 :ref:`mlir-06-06-03` 的标准路径完全共享。
下一节 :ref:`mlir-08-08-04` 将把 Dialect 和 Pass 集成到独立的 ``mydsl-opt`` 工具中。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
