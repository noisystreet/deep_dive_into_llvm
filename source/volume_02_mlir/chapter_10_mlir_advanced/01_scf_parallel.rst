.. _mlir-10-10-01:

=========================
SCF 并行优化
=========================

SCF（Structured Control Flow）Dialect 提供了三种级别的并行化支持：
``scf.parallel``、``scf.for`` 的 ``thread_local`` 属性、以及隐式并行语义。

.. rst-class:: center

   SCF 的并行优化是 MLIR 中编译器自动并行化的关键入口。

.. admonition:: 编译器自动并行化的梦想与现实
   :class: note

   编译器的**自动并行化**——让编译器自动识别可以并行执行的代码片段
   并生成多线程代码——这是一个在编译器领域存在了 40 多年的梦想。

   上世纪 80-90 年代，很多研究项目试图在 Fortran 编译器上实现自动
   并行化（如 Polaris、SUIF）。它们取得了一定的成功，但效果很有限：
   只能处理模式非常规整的循环（如连续的内存访问、无复杂控制流），
   对现实世界中的代码效果不佳。

   MLIR 并没有放弃这个梦想，而是换了一个更现实的思路：**不试图自动发现
   并行性，而是让上层 IR 显式标记并行性**。

   ``scf.parallel`` 和 ``scf.for`` 的区别就是这种思路的体现：
   程序员（或前端编译器）已经知道哪些循环可以并行，只需用 ``scf.parallel``
   标记出来。MLIR 的后端负责将这些标记映射到目标平台的并行机制上
   （CPU 上的 OpenMP 线程、GPU 上的线程束、加速器上的 SIMD）。

   这个思路在今天取得了比"纯自动并行化"更好的效果：
   - TensorFlow/PyTorch 的图编译器知道哪些操作为独立（可以并行执行），通过 ``scf.parallel`` 传递这个信息
   - 硬件设计工具知道硬件模块是并行执行的，同样通过 MLIR 的并行语义传递
   - IREE 的流执行模型利用 ``scf.parallel`` 在不同硬件设备间调度计算

   所以，MLIR 的"并行"不是 Magic——它是把人类已知的信息，
   通过编译器可以理解的方式，传递给代码生成后端。

scf.parallel
==================

``scf.parallel`` 是 SCF 中**显式的并行循环**：

.. code-block:: text

   // 串行版本（scf.for）
   %r = scf.for %i = %c0 to %N step %c1
       iter_args(%acc = %init) -> f32 {
       %v = arith.addf %acc, %val : f32
       scf.yield %v : f32
   }

   // 并行版本（scf.parallel）
   %r = scf.parallel (%i) = (%c0) to (%N) step (%c1) {
       %v = arith.addf ... // 每次迭代独立
       scf.reduce(%v, %other : f32) {
           // 归约操作
       }
   }

``scf.parallel`` 与 ``scf.for`` 的关键区别：

- **无数据依赖**：所有迭代可以并行执行
- **归约操作**：使用 ``scf.reduce`` 处理跨迭代的聚合
- **任意顺序**：迭代顺序不确定

归约操作详解
==================

.. code-block:: text

   // 归约操作
   scf.parallel (%i) = (%c0) to (%N) step (%c1) {
       // 计算
       %v = some_computation(%i)
       // 归约：将所有 v 累加
       scf.reduce(%v : f32) {
           ^bb0(%lhs: f32, %rhs: f32):
               %sum = arith.addf %lhs, %rhs : f32
               scf.reduce.return %sum : f32
       }
   }

归约操作保证了无论迭代执行的顺序如何，最终结果都是正确的。

分布到线程
==================

当并行循环降级到 CPU 时，迭代空间可以分布到多个线程：

.. code-block:: console

   $ mlir-opt --convert-parallel-loops-to-gpu \
       --gpu-kernel-outlining input.mlir

   # 或者使用 OpenMP
   $ mlir-opt --convert-parallel-loops-to-openmp input.mlir

OpenMP 后端：

.. code-block:: text

   // MLIR scf.parallel
   scf.parallel (%i) = (%c0) to (%N) step (%c1) {
       body(%i)
   }

   // 降级到 OpenMP
   // #pragma omp parallel for
   // for (int i = 0; i < N; i++) { body(i); }

GPU 后端：

.. code-block:: text

   // MLIR scf.parallel → GPU
   // 外层映射到 blockIdx，内层映射到 threadIdx

并行化的性能考量
========================

使用 ``scf.parallel`` 时，以下因素影响性能：

1. **迭代粒度**：每次迭代的工作量应足够大，以抵消线程调度的开销
2. **数据局部性**：尽量让同一 block 的线程访问连续内存
3. **归约次数**：太多归约会引入同步开销

并行优化示例
==================

.. code-block:: text

   // 优化的并行矩阵乘法
   scf.parallel (%i, %j) = (%c0, %c0) to (%N, %M) step (%c1, %c1) {
       %sum = scf.for %k = %c0 to %K step %c1
           iter_args(%acc = %c0) -> f32 {
           %a = tensor.extract %A[%i, %k] : tensor<NxKxf32>
           %b = tensor.extract %B[%k, %j] : tensor<KxMxf32>
           %p = arith.mulf %a, %b : f32
           %s = arith.addf %acc, %p : f32
           scf.yield %s : f32
       }
       %C = tensor.insert %sum into %C_init[%i, %j] : tensor<NxMxf32>
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
