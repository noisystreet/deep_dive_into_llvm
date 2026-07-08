.. _mlir-05-05-03:

=========================
Dialect Conversion
=========================

Dialect Conversion 是 MLIR **渐进降级** （Progressive Lowering）的核心机制。
它将一个 Dialect 的 Operation 转换为另一个 Dialect 的等价 Operation。

.. rst-class:: center

   Conversion 的本质：把"高层的 Operation"翻译成"低层的 Operation"。

Conversion 的核心概念
============================

Dialect Conversion 涉及三个核心角色：

.. mermaid::

   flowchart LR
       A[源 Operation] --> B[ConversionPattern]
       B --> C[目标 Operation]
       D[TypeConverter] --> B
       E[TargetMaterialization] --> C
       F[SourceMaterialization] --> B

       style A fill:#ff9800,color:#fff
       style C fill:#4a9eff,color:#fff
       style B fill:#7c4dff,color:#fff

1. **ConversionPattern**：定义源 Op 到目标 Op 的转换逻辑
2. **TypeConverter**：管理类型之间的映射（如 ``tensor`` → ``memref`` ）
3. **Materialization**：处理类型不匹配时的转换操作

ConversionPattern
=======================

.. code-block:: cpp

   struct MyOpConversion : public OpConversionPattern<MyOp> {
       MyOpConversion(MLIRContext *ctx, TypeConverter &typeConverter)
           : OpConversionPattern<MyOp>(typeConverter, ctx) {}

       LogicalResult matchAndRewrite(MyOp op, MyOp::Adaptor adaptor,
           ConversionPatternRewriter &rewriter) const override {

           // adaptor 中的操作数已经完成了类型转换
           // 不需要手动处理类型映射

           // 创建新的目标 Op
           rewriter.replaceOpWithNewOp<TargetOp>(
               op, /*result types*/, adaptor.getOperands());
           return success();
       }
   };

**Adaptor 机制**

``Adaptor`` 是 Conversion 的一个重要机制。它自动完成了**操作数的类型映射**：

.. code-block:: cpp

   // 假设 MyOp 的参数类型是 tensor<4xf32>
   // 而 TypeConverter 把 tensor<4xf32> 映射为 memref<4xf32>
   // 那么 Adaptor 中的操作数类型已经自动转换为 memref<4xf32>

   LogicalResult matchAndRewrite(MyOp op, MyOp::Adaptor adaptor,
       ConversionPatternRewriter &rewriter) const override {
       // op.getOperand(0).getType() → tensor<4xf32>
       // adaptor.getOperands()[0].getType() → memref<4xf32>
   }

TypeConverter
======================

TypeConverter 定义了类型之间的映射规则：

.. code-block:: cpp

   TypeConverter converter;

   // 添加类型转换规则
   converter.addConversion([](TensorType type) -> Type {
       // 将 tensor<...> 转换为 memref<...>
       return MemRefType::get(type.getShape(), type.getElementType());
   });

   // 添加回退规则（所有未注册的类型保持不变）
   converter.addConversion([](Type type) { return type; });

   // 添加目标合法化规则
   converter.addTargetMaterialization([](OpBuilder &builder,
       MemRefType type, ValueRange inputs, Location loc) -> Value {
       // 当类型不匹配时，创建从 tensor 到 memref 的转换操作
       return builder.create<UnrealizedConversionCastOp>(
           loc, type, inputs).getResult(0);
   });

   converter.addSourceMaterialization([](OpBuilder &builder,
       TensorType type, ValueRange inputs, Location loc) -> Value {
       // 从 memref 转回 tensor（反向转换）
       return builder.create<UnrealizedConversionCastOp>(
           loc, type, inputs).getResult(0);
   });

完整的 Conversion 
=========================

将 ``arith`` 的 Op 转换到 ``LLVM`` Dialect：

.. code-block:: cpp

   struct ArithToLLVMConversionPass
       : public PassWrapper<ArithToLLVMConversionPass,
                            OperationPass<ModuleOp>> {

       void runOnOperation() override {
           ModuleOp module = getOperation();
           ConversionTarget target(getContext());

           // 目标 Dialect：只接受 LLVM Dialect
           target.addLegalDialect<LLVM::LLVMDialect>();
           // 源 Dialect：需要被转换
           target.addIllegalDialect<arith::ArithDialect>();

           TypeConverter converter;
           // 类型映射：MLIR 的 i32 → LLVM 的 i32
           converter.addConversion([](IntegerType type) -> Type {
               return IntegerType::get(type.getContext(),
                   type.getWidth());
           });
           converter.addConversion([](FloatType type) -> Type {
               return type;
           });

           RewritePatternSet patterns(&getContext());
           // 添加 arith → LLVM 的转换 pattern
           arith::populateArithToLLVMConversionPatterns(
               converter, patterns);

           if (failed(applyFullConversion(module, target,
                                          std::move(patterns)))) {
               signalPassFailure();
           }
       }
   };

Partial vs Full Conversion
=================================

MLIR 提供两种 conversion 模式：

**Full Conversion**

所有源 Operation 必须被转换，否则报错：

.. code-block:: cpp

   applyFullConversion(module, target, std::move(patterns));

**Partial Conversion**

允许某些 Operation 不被转换：

.. code-block:: cpp

   applyPartialConversion(module, target, std::move(patterns));

Partial Conversion 适用于分阶段降级——每个阶段只转换一部分 Operation。

动态与静态合法化
=======================

**静态合法化**

在 ConversionTarget 中设置：

.. code-block:: cpp

   target.addLegalDialect<LLVM::LLVMDialect>();
   target.addIllegalDialect<arith::ArithDialect>();
   target.addLegalOp<MyOp>();

**动态合法化**

某些 Operation 是否合法取决于其属性：

.. code-block:: cpp

   target.addDynamicallyLegalOp<arith::AddIOp>(
       [](arith::AddIOp op) {
           // 只有 i32 类型才合法
           return op.getType().isInteger(32);
       });

源码走读：DialectConversion 框架
======================================

Dialect Conversion 的核心实现在
`DialectConversion.cpp <file:///workspace/llvm-project/mlir/lib/Transforms/Utils/DialectConversion.cpp>`__ 。
接口头文件为
`DialectConversion.h <file:///workspace/llvm-project/mlir/include/mlir/Transforms/DialectConversion.h>`__ 。

``applyFullConversion`` 与 ``applyPartialConversion`` 的区别在于
**合法化检查的时机和严格程度**：

- Full Conversion：目标 Dialect 之外的 Operation 必须全部被转换，否则失败
- Partial Conversion：允许保留部分未转换的 Operation，适合分阶段降级

:ref:`mlir-06-06-03` 中的 arith/func → LLVM 降级就是 Full Conversion 的典型场景。
Toy Ch6 的 ``ToyToLLVMLoweringPass`` （:ref:`mlir-08-08-03`）也使用同一框架。

``TypeConverter`` 负责跨 Dialect 的类型映射——例如 ``memref`` 描述符
到 ``!llvm.struct<...>`` 的转换，由 ``LLVMTypeConverter`` 统一管理。

动手验证
==========

观察 Dialect Conversion 的完整降级：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts

输出应只含 ``llvm`` Dialect 的操作。若遗漏某个 Pass，
``--reconcile-unrealized-casts`` 会报告未消除的 cast——
这正是 Conversion 框架的完整性检查。

本章小结
========

Dialect Conversion 处理跨 Dialect 的类型变化和 Operation 替换，
是 MLIR 渐进降级管道的核心机制。下一节 :ref:`mlir-05-05-04` 介绍
如何将多个 Pass 编排为 Pipeline 。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
