.. _mlir-appendix-02-dialect-cheatsheet:

=================
Dialect 速查表
=================

本表汇总第二卷涉及的主要 Dialect，按抽象层次从高到低排列。
用于快速定位"某个语义应该用哪个 Dialect 表达"。

.. rst-class:: center

   记住渐进降级方向：高层 Dialect → 低层 Dialect → LLVM Dialect → LLVM IR

按抽象层次分类
==================

领域特定层
------------------

.. list-table::
   :header-rows: 1

   * - Dialect
     - 前缀
     - 典型操作
     - 主要用途
   * - StableHLO
     - ``stablehlo.``
     - ``dot_general``, ``all_reduce``
     - ML 计算图，框架互通
   * - TOSA
     - ``tosa.``
     - ``conv2d``, ``matmul``
     - 推理引擎标准算子集
   * - Toy
     - ``toy.``
     - ``mul``, ``struct_constant``
     - Tutorial 自定义语言

结构化计算层
------------------

.. list-table::
   :header-rows: 1

   * - Dialect
     - 前缀
     - 典型操作
     - 主要用途
   * - linalg
     - ``linalg.``
     - ``matmul``, ``generic``, ``elemwise_binary``
     - 结构化线性代数
   * - tensor
     - ``tensor.``
     - ``extract``, ``insert``, ``empty``
     - 不可变张量值语义
   * - scf
     - ``scf.``
     - ``for``, ``if``, ``while``
     - 结构化控制流
   * - cf
     - ``cf.``
     - ``br``, ``cond_br``
     - 非结构化控制流图

基础原语层
------------------

.. list-table::
   :header-rows: 1

   * - Dialect
     - 前缀
     - 典型操作
     - 主要用途
   * - func
     - ``func.``
     - ``func``, ``call``, ``return``
     - 函数定义与调用
   * - arith
     - ``arith.``
     - ``addi``, ``addf``, ``cmpi``, ``constant``
     - 标量算术
   * - math
     - ``math.``
     - ``sqrt``, ``sin``, ``exp``
     - 数学函数
   * - memref
     - ``memref.``
     - ``alloc``, ``load``, ``store``
     - 可变内存引用

后端与运行时层
------------------

.. list-table::
   :header-rows: 1

   * - Dialect
     - 前缀
     - 典型操作
     - 主要用途
   * - LLVM
     - ``llvm.``
     - ``func``, ``add``, ``load``, ``call``
     - LLVM IR 的 MLIR 映射
   * - async
     - ``async.``
     - ``execute``, ``await``, ``create_group``
     - 结构化异步执行
   * - vector
     - ``vector.``
     - ``load``, ``store``, ``reduction``
     - 显式 SIMD 向量操作
   * - gpu
     - ``gpu.``
     - ``launch``, ``memcpy``
     - GPU kernel 启动

常用降级管道
==================

CPU 端到端
------------------

.. code-block:: console

   mlir-opt input.mlir \
       --one-shot-bufferize="bufferize-function-boundaries" \
       --convert-linalg-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts

向量加速
------------------

.. code-block:: console

   mlir-opt input.mlir \
       --linalg-vectorize \
       --convert-vector-to-llvm \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       --reconcile-unrealized-casts

JIT 执行
------------------

.. code-block:: console

   mlir-opt ... input.mlir | mlir-cpu-runner -e main -entry-point-result=i32

常用 mlir-opt Pass 速查
============================

.. list-table::
   :header-rows: 1

   * - Pass 名称
     - 作用
   * - ``--one-shot-bufferize``
     - tensor → memref
   * - ``--convert-linalg-to-loops``
     - linalg → scf 循环
   * - ``--convert-scf-to-cf``
     - scf → cf 控制流
   * - ``--convert-arith-to-llvm``
     - arith → LLVM Dialect
   * - ``--convert-func-to-llvm``
     - func → LLVM Dialect
   * - ``--convert-memref-to-llvm``
     - memref → LLVM 描述符
   * - ``--reconcile-unrealized-casts``
     - 检查降级完整性
   * - ``--linalg-vectorize``
     - linalg → vector 向量化
   * - ``--async-to-async-runtime``
     - async → 运行时调用

ODS 文件速查
==================

.. list-table::
   :header-rows: 1

   * - Dialect
     - ODS 文件路径
   * - builtin
     - ``mlir/include/mlir/IR/BuiltinOps.td``
   * - func
     - ``mlir/include/mlir/Dialect/Func/IR/FuncOps.td``
   * - arith
     - ``mlir/include/mlir/Dialect/Arith/IR/ArithOps.td``
   * - scf
     - ``mlir/include/mlir/Dialect/SCF/IR/SCFOps.td``
   * - linalg
     - ``mlir/include/mlir/Dialect/Linalg/IR/LinalgOps.td``
   * - LLVM
     - ``mlir/include/mlir/Dialect/LLVMIR/LLVMOps.td``
   * - async
     - ``mlir/include/mlir/Dialect/Async/IR/AsyncOps.td``
   * - vector
     - ``mlir/include/mlir/Dialect/Vector/IR/VectorOps.td``

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
