.. _mlir-10-10-04:

===================
MLIR JIT Pipeline
===================

MLIR 支持将程序直接 JIT 编译为机器码并执行，无需显式调用 LLVM 工具链。
JIT Pipeline 是 MLIR 编译管道和运行时执行之间的桥梁。

.. rst-class:: center

   MLIR JIT 的核心：``mlir-cpu-runner`` 内部封装了 ORC JIT。

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

Lazy JIT（延迟编译）只在函数首次被调用时才编译。这可以**减少启动时间**：

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

- **快速原型验证**：不需要 ``llc`` 和 ``clang`` 的完整编译流程
- **动态代码生成**：运行时生成和编译 MLIR 程序
- **调试**：快速测试降级管道的正确性

JIT 中的性能优化
========================

.. code-block:: console

   # 在 JIT 前使用 LLVM Pass 优化
   $ mlir-opt ... input.mlir | opt -O2 | mlir-cpu-runner ...

   # 使用更大的代码缓存
   $ LLD_FORCE_DEBUG_PACKRAT=1 mlir-cpu-runner ...

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
