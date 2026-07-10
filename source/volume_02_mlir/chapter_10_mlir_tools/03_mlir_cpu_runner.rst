.. _mlir-11-09-03:

======================
mlir-cpu-runner
======================

``mlir-cpu-runner`` 将 MLIR 程序 JIT 编译为机器码并在 CPU 上执行。
它内部使用 LLVM ORC JIT 引擎。

.. rst-class:: center

   ``mlir-cpu-runner`` = ``mlir-translate`` + ``lli`` （LLVM JIT）。

.. admonition:: 端到端验证：从 .mlir 到 stdout 只需一条命令
   :class: tip

   开发自定义 Dialect 时， ``mlir-cpu-runner`` 是最高效的冒烟测试——
   它把降级、翻译、JIT、执行串成一条命令，直接打印 ``main`` 的返回值。

   内部流程：MLIR IR → LLVM Dialect → LLVM IR → ORC JIT → 调用 ``main`` 。
   与第一卷 ``lli`` 的区别只是前端多了一步 MLIR 降级。
   如果 ``mlir-cpu-runner`` 能跑通，说明你的 Dialect 至少能走完整
   CPU 管道——这比分别调试每个 Pass 高效得多。

基本用法
==============

.. code-block:: console

   # 直接将 MLIR 降级后通过 JIT 运行
   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts \
       input.mlir | mlir-cpu-runner -e main -entry-point-result=i32

**关键参数** ：

.. code-block:: console

   -e main                         # 入口函数名
   -entry-point-result=i32         # 入口函数返回值类型
   --shared-libs=libmlir_runner.so # 共享库（I/O 函数等）
   --main-func=main                # 默认的入口函数名

端到端示例
==================

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
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       add.mlir | mlir-cpu-runner -e main -entry-point-result=i32

   // 输出：42

带张量输入/输出
======================

.. code-block:: text

   // matmul.mlir
   func.func @main() -> f32 {
       %A = arith.constant dense<[1.0, 2.0, 3.0, 4.0]> : tensor<2x2xf32>
       %B = arith.constant dense<[5.0, 6.0, 7.0, 8.0]> : tensor<2x2xf32>
       %C = linalg.matmul ins(%A, %B : tensor<2x2xf32>, tensor<2x2xf32>)
           outs(%init : tensor<2x2xf32>) -> tensor<2x2xf32>
       // ...
   }

.. code-block:: console

   $ mlir-opt \
       --one-shot-bufferize \
       --linalg-lower-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       matmul.mlir | mlir-cpu-runner -e main -entry-point-result=f32

运行时共享库
======================

``mlir-cpu-runner`` 需要加载共享库来提供运行时支持：

.. code-block:: console

   $ mlir-cpu-runner \
       --shared-libs=libmlir_c_runner_utils.so,libmlir_runner_utils.so \
       -e main -entry-point-result=i32

常用的共享库：

- ``libmlir_runner_utils.so`` ：MLIR 运行时工具（打印等）
- ``libmlir_c_runner_utils.so`` ：C 运行时工具
- ``libmlir_async_runtime.so`` ：异步运行时

内部实现
==================

``mlir-cpu-runner`` 内部流程：

.. code-block:: text

   MLIR (LLVM Dialect) → LLVM IR → ORC JIT → 执行

   1. 接收 LLVM Dialect 的 MLIR
   2. 用 mlir-translate 转换为 LLVM IR
   3. 创建 LLVM ORC JIT 实例
   4. 编译 LLVM IR
   5. 查找入口函数并执行
   6. 返回结果

与 mlir-translate 的关系
============================

.. code-block:: console

   # 等价于：
   mlir-opt ... input.mlir \
       | mlir-translate --mlir-to-llvmir -o - \
       | lli -entry-function=main -

   # 但更简洁：
   mlir-opt ... input.mlir \
       | mlir-cpu-runner -e main -entry-point-result=i32

源码走读：JitRunner 与 ExecutionEngine
======================================

``mlir-cpu-runner`` 的实现在
`JitRunner.cpp <file:///workspace/llvm-project/mlir/lib/ExecutionEngine/JitRunner.cpp>`__ 。
它内部调用 ``ExecutionEngine::create`` （`ExecutionEngine.cpp <file:///workspace/llvm-project/mlir/lib/ExecutionEngine/ExecutionEngine.cpp>`__），
完成 MLIR → LLVM IR → ORC JIT → 执行的完整链路。

Toy Ch7 的 ``toyc.cpp`` （:ref:`mlir-09-09-04`）使用同一套 API，
区别是 Toy 从前端源码生成 MLIR，而 ``mlir-cpu-runner`` 直接接收
已降级到 LLVM Dialect 的 MLIR 输入。

这与第一卷 :ref:`chapter-09-03-lli-and-jit-tools` 中的 ``lli`` 工具类比：
``lli`` 解释执行 LLVM IR ， ``mlir-cpu-runner`` 先翻译再 JIT 执行。

动手验证
==========

确认降级管道可为 JIT 准备输入：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-translate --mlir-to-llvmir | opt -O2 -S

本章小结
========

``mlir-cpu-runner`` 缩短了 MLIR 程序的验证循环，是开发降级管道时的利器。
:ref:`mlir-11-11-04` 有更详细的 JIT Pipeline 分析。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
