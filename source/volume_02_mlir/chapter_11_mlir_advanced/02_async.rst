.. _mlir-11-11-02:

===================
Async Dialect
===================

Async Dialect 是 MLIR 中用于**异步执行**的 Dialect。它提供了一组 Operation
来创建、运行和同步异步任务。

.. rst-class:: center

   Async Dialect 的核心抽象：``async.execute`` 创建一个异步任务，
   ``async.await`` 等待它完成。

.. admonition:: 异步 Dialect：编译器里的 Future/Promise
   :class: note

   ``async.execute`` + ``async.await`` 的组合等价于大多数语言中的
   ``Future`` 模式——创建异步任务，稍后等待结果。MLIR 选择在 IR 层
   显式表达异步，而非依赖运行时的线程池魔法。

   降级时，``async-to-async-runtime`` 将 Op 映射为 ``async.runtime``
   的 C API 调用（创建任务、入队、等待）。这让 MLIR 可以优化
   **异步任务的创建和调度**——例如消除冗余的 ``async.await`` ，
   或合并相邻的 ``async.execute`` 。

   IREE 和 TensorFlow 的异步执行路径都借鉴了这一抽象。

基本操作
==================

**创建和执行异步任务**

.. code-block:: text

   // 创建一个异步任务
   %token = async.execute {
       // 在另一个线程上执行
       %result = arith.addi %a, %b : i32
       async.yield %result : i32
   } : !async.token<i32>

   // 等待异步任务完成
   %value = async.await %token : !async.token<i32>

**无返回值的异步任务**

.. code-block:: text

   // 创建一个无返回值的异步任务
   %token = async.execute {
       // 执行一些副作用操作
       call @print(%val) : (i32) -> ()
   } : !async.token

   // 等待完成
   async.await %token : !async.token

Group 操作
==================

Async Group 让多个异步任务可以组合：

.. code-block:: text

   // 创建一个 group
   %group = async.create_group : !async.group

   // 将 token 添加到 group
   async.add_to_group %token, %group : !async.token, !async.group

   // 等待 group 中所有任务完成
   async.await_all %group : !async.group

**示例：并发执行多个任务**

.. code-block:: text

   %group = async.create_group : !async.group

   // 启动三个并行任务
   %t1 = async.execute { ... async.yield : i32 }
   async.add_to_group %t1, %group

   %t2 = async.execute { ... async.yield : i32 }
   async.add_to_group %t2, %group

   %t3 = async.execute { ... async.yield : i32 }
   async.add_to_group %t3, %group

   // 等待所有完成
   async.await_all %group : !async.group

降级路径
==================

Async Dialect 的降级有两种模式：

**1. 线程池模式（多线程）**

.. code-block:: console

   $ mlir-opt --async-to-async-runtime \
       --convert-async-runtime-to-llvm \
       input.mlir

降级后使用线程池来执行异步任务。

**2. 内联模式（单线程）**

.. code-block:: console

   $ mlir-opt --async-to-async-runtime \
       --async-runtime-create-group=false \
       input.mlir

内联模式将所有异步任务转化为同一线程上的顺序执行。

Async Dialect 的使用场景
========================

Async Dialect 在 MLIR 管道中的典型位置：

.. code-block:: text

   1. 高层 Dialect（如 linalg）→ 识别可并行的操作
   2. 包装为 async.execute
   3. 降级为运行时调用
   4. 最终映射到线程池（CPU）或 CUDA streams（GPU）

常见场景包括：

- **数据并行操作** ：同时对张量的不同部分执行相同计算
- **流水线执行** ：将一个计算划分为不同阶段，阶段间异步传递数据
- **I/O 与计算的交叠** ：在计算进行的同时异步加载数据

源码走读：async.execute 的语义
======================================

``async.execute`` 是 Async Dialect 的核心操作，其定义在
`AsyncOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Async/IR/AsyncOps.td>`__。

TableGen 中的描述非常关键：

.. code-block:: text

   The `body` region attached to the `async.execute` operation semantically
   can be executed concurrently with the successor operation.

注意 "semantically"（语义上）这个词——``async.execute`` 并不承诺真正的并行，
实际执行策略由后续降级决定。注释列出了三种可能：

1. 完全顺序执行（body 完成后才执行后继）
2. 多线程并行（body 在独立线程上运行）
3. 协程式交错执行

这种"语义与执行策略分离"的设计，让高层优化可以在 Async Dialect 层
识别并行机会，而不必过早绑定到某个运行时。

源码走读：降级到运行时
======================================

``--async-to-async-runtime`` 由
`AsyncToAsyncRuntime.cpp <file:///workspace/llvm-project/mlir/lib/Dialect/Async/Transforms/AsyncToAsyncRuntime.cpp>`__
实现。它将 ``async.execute`` 降级为对 ``_mlir_async_runtime_*`` 函数的调用，
最终通过 ``--convert-async-runtime-to-llvm`` 映射到 LLVM IR。

降级路径与第一卷 :ref:`chapter-08-03-orc-jit-architecture` 讨论的
异步执行模型形成对照：MLIR 在 Dialect 层表达"可并发"，在运行时层
落地为线程池或内联执行。

动手验证
==========

观察 Async Dialect 的 IR 结构（无需完整运行时）：

.. code-block:: console

   cat > /tmp/async_demo.mlir << 'EOF'
   func.func @compute(%a: i32, %b: i32) -> i32 {
     %token = async.execute -> !async.value<i32> {
       %sum = arith.addi %a, %b : i32
       async.yield %sum : i32
     }
     %result = async.await %token : !async.value<i32>
     func.return %result : i32
   }
   EOF
   mlir-opt /tmp/async_demo.mlir

输出中 ``async.execute`` 的 body region 和 ``async.await`` 的同步语义
清晰可见。若要进一步降级，需要加上 ``--async-to-async-runtime`` 等 Pass。

本章小结
========

Async Dialect 在 MLIR 中扮演"结构化并发"的角色：它用 Region 封装可并发任务，
用 Token/Group 管理同步，把执行策略推迟到降级阶段决定。
在端到端管道中，它通常位于 linalg 并行化之后、LLVM 运行时之前。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
