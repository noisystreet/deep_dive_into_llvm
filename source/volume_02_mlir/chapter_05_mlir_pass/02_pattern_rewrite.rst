.. _mlir-05-05-02:

=========================
Pattern Rewrite 框架
=========================

Pattern Rewrite 是 MLIR 中最强大、最常用的转换机制。它基于**模式匹配**
来识别 IR 中的特定操作，并用新的操作替换它们。

.. rst-class:: center

   "Pattern Rewrite = 匹配（match） + 替换（rewrite）"

ODE 的 Rewrite 系统比 LLVM 的 InstCombine 更灵活——它支持
**多操作数匹配**、**嵌套模式**和**条件约束**。

基本 Pattern
==================

一个最简单的 Rewrite Pattern：

.. code-block:: cpp

   // 模式：将 addi(x, 0) 替换为 x
   struct AddZeroFolder : public OpRewritePattern<arith::AddIOp> {
       AddZeroFolder(MLIRContext *context)
           : OpRewritePattern<arith::AddIOp>(context) {}

       LogicalResult matchAndRewrite(arith::AddIOp op,
           PatternRewriter &rewriter) const override {

           // 检查是否有操作数是 0
           Value lhs = op.getLhs();
           Value rhs = op.getRhs();

           if (matchPattern(lhs, m_Zero())) {
               rewriter.replaceOp(op, rhs);
               return success();
           }
           if (matchPattern(rhs, m_Zero())) {
               rewriter.replaceOp(op, lhs);
               return success();
           }
           return failure();
       }
   };

Pattern 的核心方法
=======================

每个 pattern 都要实现 ``matchAndRewrite`` 方法：

.. code-block:: cpp

   LogicalResult matchAndRewrite(MyOp op,
       PatternRewriter &rewriter) const override {
       // match：检查是否匹配
       // rewrite：执行替换
       //       ↓
       // match 失败时返回 failure()
       // match 成功并 rewrite 后返回 success()
   }

**PatternRewriter 提供的方法**

.. list-table:: PatternRewriter 核心方法
   :header-rows: 1

   * - 方法
     - 功能
     - 示例
   * - ``replaceOp``
     - 用新值替换 op 的结果
     - ``rewriter.replaceOp(op, newVal)``
   * - ``eraseOp``
     - 删除 op
     - ``rewriter.eraseOp(op)``
   * - ``createOp``
     - 在当前位置创建新的 op
     - ``rewriter.create<arith::AddIOp>(loc, ...)``
   * - ``setInsertionPoint``
     - 设置插入位置
     - ``rewriter.setInsertionPoint(op)``
   * - ``inlineBlock``
     - 内联一个 Block
     - ``rewriter.inlineBlock(block)``
   * - ``mergeBlocks``
     - 合并两个 Block
     - ``rewriter.mergeBlocks(src, dest)``
   * - ``clone``
     - 克隆 op
     - ``rewriter.clone(op)``
   * - ``replaceOpWithNewOp``
     - 用新的 op 类型替换
     - ``rewriter.replaceOpWithNewOp<NewOp>(op, ...)``

通用匹配器（Common Match）
===============================

MLIR 提供了一组便捷的匹配器（在 ``mlir/IR/Matchers.h`` ）：

.. code-block:: cpp

   // 匹配常量模式
   matchPattern(val, m_Zero())                         // 匹配 0
   matchPattern(val, m_One())                          // 匹配 1
   matchPattern(val, m_Constant())                     // 匹配任意常量

   // 匹配特定 Op
   matchPattern(val, m_Op<arith::AddIOp>())            // 匹配 addi

   // 匹配结果值
   matchPattern(val, m_Result<0>(m_Op<arith::AddIOp>()))  // addi 的第 0 个结果

   // 链式匹配
   matchPattern(val, m_Op<arith::AddIOp>(m_Zero(), m_One()))
   // 匹配 addi(0, 1)

创建和运行 Pattern
=========================

**创建 Pattern 集合**

.. code-block:: cpp

   // 创建 Pattern 列表
   RewritePatternSet patterns(ctx);
   patterns.add<AddZeroFolder, OtherPattern>(ctx);
   patterns.add<YetAnotherPattern>(ctx, /*benefit=*/2);

   // 也可以从其他 Dialect 的 Canonicalization 模式继承
   arith::ArithDialect::getCanonicalizationPatterns(patterns);

**应用 Pattern：GreedyPatternRewriteDriver**

.. code-block:: cpp

   // 贪心遍历：不断应用 pattern 直到 IR 不再变化
   if (failed(applyPatternsAndFoldGreedily(func, std::move(patterns)))) {
       signalPassFailure();
   }

**应用 Pattern：特定区域的遍历**

.. code-block:: cpp

   // 只在特定区域应用
   GreedyRewriteConfig config;
   config.strictMode = GreedyRewriteStrictness::AnyOp;
   (void)applyPatternsAndFoldGreedily(op, std::move(patterns), config);

Pattern 的优先级
======================

Pattern 的优先级由 ``benefit`` 参数控制：

.. code-block:: cpp

   // benefit 越高，优先级越高
   patterns.add<HighPriorityPattern>(ctx, /*benefit=*/5);
   patterns.add<LowPriorityPattern>(ctx,  /*benefit=*/1);

**内置 Pattern 的默认 benefit**：

.. list-table:: 默认 benefit 值
   :header-rows: 1

   * - Pattern 类型
     - 默认 benefit
     - 说明
   * - Canonicalization patterns
     - 1
     - 标准规范化
   * - Fold patterns
     - 2
     - 常量折叠
   * - 自定义 pattern
     - 0
     - 最低优先级

如果你希望某条 pattern 优先匹配，设置 ``benefit > 1``。

Canonicalizer Pass
=======================

MLIR 有内置的 Canonicalizer Pass，它自动应用所有 Dialect 注册的
规范化 pattern：

.. code-block:: cpp

   // 在 Pass Pipeline 中使用
   pm.addPass(mlir::createCanonicalizerPass());

每个 Dialect 在 ODS 中注册的 Canonicalization pattern 都会在
Canonicalizer Pass 中被自动应用。

.. code-block:: text

   def MyOp : Op<MyDialect, "my_op"> {
       let hasCanonicalizer = 1;
   }

   // 在 MyDialect.cpp 中实现
   void MyDialect::getCanonicalizationPatterns(
       RewritePatternSet &results) const {
       results.add<MyOpFolder>(getContext());
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
