.. _mlir-11-11-04:

===================
MLIR JIT Pipeline
===================

MLIR 支持将程序直接 JIT 编译为机器码并执行，无需显式调用 LLVM 工具链。
JIT Pipeline 是 MLIR 编译管道和运行时执行之间的桥梁。

.. rst-class:: center

   MLIR JIT 的核心：``mlir-cpu-runner`` 内部封装了 ORC JIT。

.. admonition:: ExecutionEngine：MLIR 版的 LLJIT
   :class: note

   MLIR 的 ``ExecutionEngine`` 封装了 LLVM ORC JIT，API 比裸用
   ``LLJIT`` 简洁——传入降级后的 LLVM Dialect 模块，即可 JIT 执行。

   与第一卷 :ref:`chapter-08-04-lljit-and-lazy` 的 LLJIT 对比：

   - **LLJIT** — 直接加载 LLVM IR bitcode
   - **ExecutionEngine** — 先走 MLIR 降级管道，再 JIT

   典型场景：Python/Jupyter 中交互式调用 MLIR 编译的算子——
   修改 IR → ``ExecutionEngine`` 重新 JIT → 立即执行。
   这是 MLIR 走向"编译器即服务"的关键运行时组件。

JIT Pipeline 结构
========================

.. mermaid::

   flowchart LR
       A[MLIR 程序] --> B[mlir-opt 降级]
       B --> C[LLVM Dialect]
       C --> D[ModuleTranslation]
       D --> E[LLVM IR]
       E --> F[ORC JIT]
       F --> G[执行]

完整的 JIT Pipeline：

.. code-block:: console

   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts \
       input.mlir | mlir-cpu-runner -e main -entry-point-result=i32

ORC JIT 的集成
======================

MLIR 的 ``ExecutionEngine`` 封装了 LLVM ORC JIT：

.. code-block:: cpp

   #include "mlir/ExecutionEngine/ExecutionEngine.h"

   // 创建 ExecutionEngine
   auto maybeEngine = mlir::ExecutionEngine::create(
       module, /*llvmModule=*/nullptr,
       /*transform=*/[](llvm::Module &m) {
           // 在 JIT 之前对 LLVM IR 做优化
           llvm::legacy::PassManager pm;
           pm.add(llvm::createInstructionCombiningPass());
           pm.run(m);
       });

   if (!maybeEngine) {
       llvm::errs() << "Failed to create JIT engine\n";
       return;
   }

   auto &engine = *maybeEngine;

   // 调用函数
   llvm::Error error = engine->invoke("main", {});

``ExecutionEngine`` 是 ``mlir-cpu-runner`` 的核心组件。

Lazy JIT 编译
======================

Lazy JIT（延迟编译）只在函数首次被调用时才编译。这可以**减少启动时间** ：

.. code-block:: cpp

   // mlir-cpu-runner 默认使用 Lazy JIT
   // 使用 Eager JIT 可以编译全部函数但增加启动时间

   // 在 mlir-cpu-runner 中：
   // --jit-kind=orc-lazy   （默认值，延迟编译）
   // --jit-kind=orc-eager  （立即编译）

自定义运行时符号
========================

JIT 编译的程序可以链接自定义运行时函数：

.. code-block:: cpp

   // 注册自定义运行时的全局符号
   llvm::JITTargetAddress myFuncAddr =
       (llvm::JITTargetAddress)&myPrintFunc;
   engine->registerSymbols(
       [&](llvm::orc::MangleAndInterner &mangling) {
           llvm::orc::SymbolMap symbols;
           symbols[mangling("my_print")] =
               {llvm::JITEvaluatedSymbol::fromPointer(myFuncAddr)};
           return llvm::Error::success();
       });

JIT Pipeline 的应用
========================

JIT Pipeline 在以下场景中非常有用：

- **快速原型验证** ：不需要 ``llc`` 和 ``clang`` 的完整编译流程
- **动态代码生成** ：运行时生成和编译 MLIR 程序
- **调试** ：快速测试降级管道的正确性

JIT 中的性能优化
========================

.. code-block:: console

   # 在 JIT 前使用 LLVM Pass 优化
   $ mlir-opt ... input.mlir | opt -O2 | mlir-cpu-runner ...

   # 使用更大的代码缓存
   $ LLD_FORCE_DEBUG_PACKRAT=1 mlir-cpu-runner ...

源码走读：ExecutionEngine 与 ORC JIT
======================================

``mlir-cpu-runner`` 的核心是 ``ExecutionEngine`` 类，定义在
`ExecutionEngine.h <file:///workspace/llvm-project/mlir/include/mlir/ExecutionEngine/ExecutionEngine.h>`__，
实现在 `ExecutionEngine.cpp <file:///workspace/llvm-project/mlir/lib/ExecutionEngine/ExecutionEngine.cpp>`__。

文件头注释写得很清楚：

.. code-block:: text

   This file implements the execution engine for MLIR modules based on LLVM Orc
   JIT engine.

``ExecutionEngineOptions`` 结构体暴露了三个关键定制点：

1. ``llvmModuleBuilder`` —— 自定义 MLIR → LLVM IR 的翻译逻辑
2. ``transformer`` —— JIT 编译前对 LLVM Module 运行优化 Pass
3. ``sharedLibPaths`` —— 链接外部共享库以解析符号

其中 ``transformer`` 回调正是文档前文示例中插入 ``InstCombine`` 的入口。
这与第一卷 :ref:`chapter-08-04-lljit-and-lazy` 讨论的 LLJIT 架构一脉相承——
MLIR 的 ExecutionEngine 本质上是在 MLIR Module 和 LLVM ORC JIT 之间
加了一层翻译和符号管理。

JitRunner 的角色
======================

除了库 API，``mlir/lib/ExecutionEngine/JitRunner.cpp`` 实现了
``mlir-cpu-runner`` 的命令行逻辑：解析参数、构建降级管道、创建
ExecutionEngine、调用入口函数并打印结果。阅读这个文件可以理解
"一条 mlir-opt | mlir-cpu-runner 命令"在源码层面的完整执行路径。

动手验证
==========

用项目示例走通 JIT 执行：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-cpu-runner -entry-point-result=i32 -e add 10 32

预期输出 ``42`` 。这条命令串联了：

1. MLIR → LLVM Dialect 降级，由 ``mlir-opt`` 完成
2. LLVM Dialect → LLVM IR 翻译，在 ``mlir-cpu-runner`` 内部完成
3. ORC JIT 编译 + 执行，由 ``ExecutionEngine`` 驱动

若要观察生成的 LLVM IR 而不执行，可以改用 ``mlir-translate`` 。

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-translate --mlir-to-llvmir

本章小结
========

MLIR JIT Pipeline 的价值在于**缩短验证循环** ：修改 Dialect 或 Pass 后，
无需走完整的 ``llc`` + ``clang`` 流程，一行命令就能编译执行。
``ExecutionEngine`` 把 MLIR 的降级成果对接到第一卷介绍的 ORC JIT 引擎，
完成从 MLIR 到可执行机器码的最后一公里。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
