.. _mlir-04-04-02:

======================
Bufferization Dialect
======================

``bufferization`` Dialect 提供了从 **tensor（值）到 memref（内存）** 的转换
操作和接口。它并不是一个"常规"的 Dialect——它的存在是为了支持 One-Shot
Bufferization Pass 的中间状态。

.. rst-class:: center

   Bufferization 是 MLIR 降级管道中 **最关键的一步**——它决定了
   变量是存在寄存器里还是内存里。

One-Shot Bufferization
============================

MLIR 的 ``--one-shot-bufferize`` Pass 一次性完成所有 tensor → memref 的转换。
它的核心思想是 **就地缓冲（in-place bufferization）** 。

.. code-block:: text

   // 缓冲化前（tensor 形式）
   func.func @add(%a: tensor<4xf32>, %b: tensor<4xf32>) -> tensor<4xf32> {
       %0 = linalg.add %a, %b : tensor<4xf32>
       func.return %0 : tensor<4xf32>
   }

   // 缓冲化后（memref 形式）
   func.func @add(%a: memref<4xf32>, %b: memref<4xf32>,
                  %out: memref<4xf32>) {
       linalg.add ins(%a, %b : memref<4xf32>, memref<4xf32>)
           outs(%out : memref<4xf32>)
       func.return
   }

**关键转变** ：

1. 返回值从 tensor 变为 memref 参数（"输出参数"风格）
2. 调用者负责分配内存
3. Operation 在原地修改输出 buffer，而非产生新 tensor

Bufferization Dialect 的操作
================================

Bufferization 在转换过程中可能插入以下操作作为中间表示：

.. code-block:: text

   // 分配一个新 buffer
   %alloc = bufferization.alloc_tensor() : tensor<4xf32>

   // 将 tensor 复制到 memref
   bufferization.materialize_in_destination
       %tensor in %memref : tensor<4xf32> -> memref<4xf32>

   // 克隆操作（当 tensor 有多个使用者时）
   %clone = bufferization.clone %memref : memref<4xf32> to memref<4xf32>

这些操作在完整的 bufferization 完成后会被消除或降级。

In-place 分析
======================

Bufferization 的核心挑战是 **决定哪些操作可以就地执行** 。

.. code-block:: text

   // 分析前
   %0 = linalg.add ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
       outs(%out : tensor<4xf32>) -> tensor<4xf32>

   // 如果 out 只被 %0 使用 → 就地更新可行
   // 如果 out 还被别处使用   → 必须分配新内存

这个分析称为 **RAUW（Replace All Uses With）分析** ，是 One-Shot Bufferize
的核心算法。它通过构建 tensor 的 use-def 链来判断每个 tensor 是否可以就地更新。

Bufferization 的配置
==========================

.. code-block:: console

   # 基本用法（自动分析 in-place）
   $ mlir-opt --one-shot-bufferize input.mlir

   # 带函数边界缓冲化
   $ mlir-opt --one-shot-bufferize="bufferize-function-boundaries" input.mlir

   # 允许内存分配
   $ mlir-opt --one-shot-bufferize="allow-unknown-ops" input.mlir

**常用选项** ：

.. list-table::
   :header-rows: 1

   * - 选项
     - 默认值
     - 说明
   * - ``bufferize-function-boundaries``
     - false
     - 跨函数边界的 bufferization
   * - ``allow-unknown-ops``
     - false
     - 允许未注册的 Op 保留 tensor 类型
   * - ``create-deallocs``
     - true
     - 自动插入 dealloc
   * - ``dialect-filter``
     - (空)
     - 只缓冲指定 Dialect 的 Op

与 memref 的转换
======================

.. code-block:: console

   # tensor → memref（One-Shot Bufferize）
   $ mlir-opt --one-shot-bufferize input.mlir

   # memref → LLVM（标准降级）
   $ mlir-opt --one-shot-bufferize \
       --convert-linalg-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       input.mlir
