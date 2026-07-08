.. _mlir-10-10-02:

===================
Async Dialect
===================

Async Dialect 是 MLIR 中用于**异步执行**的 Dialect。它提供了一组 Operation
来创建、运行和同步异步任务。

.. rst-class:: center

   Async Dialect 的核心抽象：``async.execute`` 创建一个异步任务，
   ``async.await`` 等待它完成。

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

- **数据并行操作**：同时对张量的不同部分执行相同计算
- **流水线执行**：将一个计算划分为不同阶段，阶段间异步传递数据
- **I/O 与计算的交叠**：在计算进行的同时异步加载数据

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
