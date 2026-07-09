.. _mlir-02-02-04:

=======================
位置信息与诊断
=======================

MLIR 在 IR 的每一级都保留了**源码位置信息**。每个 Operation、Block 参数、
乃至 Attribute 都可以关联一个 ``Location``。这是 MLIR 比 LLVM IR 更强大
的特性之一——**在多层降级过程中，位置信息不会丢失**。

.. rst-class:: center

   LLVM IR 中，一个指令的位置信息在优化后可能丢失或变得不精确；
   MLIR 的设计确保从顶层到底层的每一步都可以追溯到源代码。

.. admonition:: 多层降级中，诊断信息为何不能丢？
   :class: note

   传统编译器在 AST → IR 降级后，优化 Pass 可能让指令的 ``debug loc``
   变得模糊甚至丢失。MLIR 把 ``Location`` 作为**一等公民**挂在每个
   Operation 上，并支持 **FusedLocation** 把多层来源合并。

   实际价值：当 ``linalg.matmul`` 降级为三层 ``scf.for`` 再变成
   ``llvm.load`` 时，错误信息仍能指向原始 Python/ONNX 代码行——
   这对 ML 框架调试至关重要。XLA 和 IREE 的用户反馈中，
   "能定位到原始模型算子" 是 Location 机制最受好评的特性之一。

Location（位置信息）
========================

MLIR 的 ``Location`` 类型支持多种格式：

.. code-block:: text

   // 文件名 + 行号
   loc("foo.c":10:5)

   // 调用栈位置
   loc(callsite("bar" at "foo.c":10:5))

   // 未知位置
   loc(unknown)

   // 名称位置（用于测试）
   loc("my_location")

位置信息可以通过 ``-mlir-print-debuginfo`` 显示：

.. code-block:: console

   $ mlir-opt -mlir-print-debuginfo input.mlir

   %0 = arith.addi %arg0, %arg1 : i32 loc("example.mlir":5:3)

FusedLoc：多级位置
=======================

在降级过程中，MLIR 可以将多级位置信息**融合**在一起：

.. code-block:: text

   // 融合位置：当前操作来自 foo.c:10:5，
   // 而 foo.c:10:5 本身来自原始 Python 脚本的 42 行
   loc(fused<"example.mlir":10:5, "generated.py":42:1>)

这使得调试时可以从 LLVM IR 一路追溯到 Python 源代码。

DiagnosticEngine（诊断引擎）
=====================================

MLIR 的诊断系统支持可插拔的**诊断处理引擎**。其工作方式与 LLVM 的 ``LLVM_DEBUG``
不同——它不是打印文本，而是发送结构化的诊断对象。

.. code-block:: cpp

   // 在 Operation 中报告错误
   return emitOpError("operand type mismatch: expected ")
          << expectedType << " but got " << actualType;

   // 在 Pass 中发出警告
   emitWarning(op->getLoc(), "this pattern is deprecated");

两种级别的诊断：
- **emitOpError**：返回并报告错误（中止操作）
- **emitWarning** / **emitRemark**：仅记录，不中止

诊断的默认目标是 stderr，但可以注册自定义处理引擎：

.. code-block:: cpp

   // 注册自定义诊断处理器
   MLIRContext context;
   context.getDiagEngine().registerHandler(
       [](Diagnostic &diag) -> LogicalResult {
           // 将诊断信息改为 JSON 格式输出
           llvm::outs() << "{\"severity\": " << diag.getSeverity()
                        << ", \"message\": \"" << diag << "\"}\n";
           return success();
       });

这会改变整个 MLIRContext 的异常处理行为，对单元测试和 IDE 集成非常有用。

Verifier（验证器）
=======================

MLIR 的验证器会在 IR 构造完成后自动运行，它检查：

1. **Operation 的正确性**：操作数数量、类型是否匹配
2. **SSA 有效性**：所有使用必须对应到定义（没有未定义的值）
3. **Block 有效性**：Block 必须终止于合法的终止操作
4. **自定义验证**：每个 Operation 的 verify() 方法

.. code-block:: cpp

   // 手动触发验证
   if (failed(module->verify())) {
       module->emitError("module verification failed");
       return failure();
   }

如果有任意验证失败，IR 会被认为是非法的。这是 MLIR 保证正确性的核心机制。

在 Pass 开发中验证 IR
===============================

在编写 Pass 时，可以在关键节点主动触发验证：

.. code-block:: cpp

   // 在每个 Pass 运行前后自动验证
   // 在注册 Pass 时开启
   passManager.addPass(std::make_unique<MyPass>());
   passManager.enableVerifier();  // 启用 Pass 间的 IR 验证

或者在 ``mlir-opt`` 中使用：

.. code-block:: console

   $ mlir-opt -verify-each=0 input.mlir    # 不进行 Pass 间验证
   $ mlir-opt -verify-each=1 input.mlir    # 每个 Pass 后验证

在开发阶段，建议始终开启 ``-verify-each`` 。

源码走读：Location 的类层次
======================================

MLIR 的位置信息不是简单的字符串，而是一棵可遍历的属性树。
``Location.h`` 的文件头注释点明了设计目标：

.. code-block:: text

   These classes provide the ability to relate MLIR objects back to source
   location position information.

（`Location.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Location.h>`__）

``LocationAttr`` 是所有位置类型的锚点。它提供 ``walk()`` 方法，
以先序遍历的方式访问嵌套的位置节点——这正是 ``FusedLoc`` 融合多级
位置信息的基础机制。

对比第一卷 :ref:`chapter-02-05-debug-info` 中的 DWARF 调试信息：
LLVM IR 的 ``!dbg`` 元数据在激进优化后可能失效或被剥离；
MLIR 把 Location 做成 Operation 的一等属性，在 Dialect Conversion 过程中
**默认保留**，这对多层降级管道中的错误诊断至关重要。

源码走读：诊断与验证
======================================

诊断引擎的入口是 ``MLIRContext::getDiagEngine()`` 。
``emitOpError`` 等方法生成 ``Diagnostic`` 对象，可以注册自定义 Handler
将其转为 JSON 或 IDE 可消费的格式——这对构建 MLIR 语言服务器尤为重要。

验证器则在 Operation 构造后自动调用每个 Op 的 ``verify()`` 方法。
源码中 ``Operation::verify()`` 会检查 SSA 有效性、Block 终止符合法性，
以及 ODS 自动生成的类型约束。这与第一卷 :ref:`chapter-02-04-metadata` 讨论的
IR 验证思想一致：在变换之前尽早发现非法 IR。

动手验证
==========

观察 Location 信息在 IR 打印中的效果：

.. code-block:: console

   cat > /tmp/loc_demo.mlir << 'EOF'
   #loc = loc("demo.mlir":3:5)
   func.func @add(%a: i32, %b: i32) -> i32 {
     %sum = arith.addi %a, %b : i32 loc(#loc)
     func.return %sum : i32
   }
   EOF
   mlir-opt /tmp/loc_demo.mlir -mlir-print-debuginfo

输出中 ``arith.addi`` 后应出现 ``loc("demo.mlir":3:5)`` 。
尝试删除 ``func.return`` 前的类型标注，观察验证器报错的格式——
错误信息会携带 Location，直接指向出错行。

本章小结
========

Location 和诊断系统是 MLIR 相比 LLVM IR 的显著优势之一：
多层降级不必牺牲可追溯性。在编写自定义 Pass 时，应始终通过
``op->getLoc()`` 报告错误，而非打印裸字符串。

这四篇核心概念文档至此告一段落。下一章 :ref:`mlir-03-index` 将进入
具体的 Dialect 世界。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
