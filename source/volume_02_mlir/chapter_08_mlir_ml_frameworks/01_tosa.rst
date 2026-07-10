.. _mlir-11-07-01:

============
TOSA Dialect
============

TOSA（Tensor Operator Set Architecture）是 MLIR 中一个**用于推理场景**
的 Dialect。它定义了一组可移植的张量操作，专为边缘设备和推理引擎设计。

.. rst-class:: center

   TOSA 的设计目标：一组稳定的、可预测性能的操作集，适合硬件加速器
   和推理引擎直接消费。

.. admonition:: TOSA vs StableHLO：一"场"没有硝烟的 Dialect 之争
   :class: note

   在 MLIR 生态中，TOSA 和 StableHLO 是**两个最重要的机器学习 Dialect**。
   它们都用于表示深度学习模型的计算图，但设计哲学截然不同。

   **StableHLO** 是 Google 推出的，它是 XLA HLO 的"稳定版"。它的设计
   目标是：能够表示 TensorFlow/JAX/PyTorch 的所有计算模式。所以它的
   操作集很丰富（100+ 操作），支持动态形状和版本化序列化。

   **TOSA** 是 Arm 和 Linaro 联合推出的，它的设计目标是：推理部署。
   它只包含了可以在硬件上高效实现的操作，不支持动态形状，原生支持
   量化（i8/int8）。

   这场"争论"的本质是：**训练 vs 推理**。
   - 训练需要灵活性（动态形状、丰富的操作集）→ StableHLO
   - 推理需要效率（固定形状、量化支持、硬件友好）→ TOSA

   实践中，很多 Pipeline 的做法是：训练时用 StableHLO，部署时先转换
   为 TOSA（如果目标硬件支持），再降级到目标后端。这样既享受了
   StableHLO 的表达能力，又获得了 TOSA 的硬件优化。

   2023 年，Google 和 Arm 的合作进一步加强：StableHLO 可以将部分操作
   降级到 TOSA，TOSA 也可以将缺失的操作提升到 StableHLO。两个生态
   不再是竞争关系，而是互补关系。

TOSA 的设计哲学
======================

**操作集稳定**：TOSA 的操作集变化缓慢，版本升级时保持向后兼容。
这与 StableHLO 不同——TOSA 更关注"最小可用集"，而不是"尽可能丰富"。

**形状固定**：TOSA 操作在编译期就知道张量形状，不处理动态形状：

.. code-block:: text

   // TOSA 操作（形状在编译期已知）
   %result = tosa.add %a, %b : (tensor<1x224x224x3xf32>, tensor<1x224x224x3xf32>) ->
       tensor<1x224x224x3xf32>

**量化优先**：TOSA 原生支持 ``i8``、``i16`` 量化类型。

TOSA 的核心操作
======================

TOSA 定义了几个核心操作类：

**元素操作**

.. code-block:: text

   tosa.add                    // 逐元素加法
   tosa.sub                    // 逐元素减法
   tosa.mul                    // 逐元素乘法
   tosa.negate                 // 逐元素取反
   tosa.clamp                  // 钳制到 [min, max]
   tosa.relun                  // ReLU-N 激活函数

**张量操作**

.. code-block:: text

   tosa.reshape                 // 重塑形状
   tosa.transpose               // 转置
   tosa.slice                   // 切片
   tosa.concat                  // 拼接
   tosa.pad                     // 填充

**卷积操作**

.. code-block:: text

   tosa.conv2d                  // 2D 卷积
   tosa.depthwise_conv2d        // 深度可分离卷积
   tosa.fully_connected         // 全连接层

**池化操作**

.. code-block:: text

   tosa.max_pool2d              // 最大池化
   tosa.avg_pool2d              // 平均池化

TOSA 与 MLIR Pipeline
===========================

TOSA 通常作为 ML 框架的**统一输入格式**，然后降级到不同的后端：

.. code-block:: console

   # TOSA → linalg → scf → LLVM
   $ mlir-opt \
       --tosa-to-linalg \
       --linalg-lower-to-loops \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       tosa_input.mlir

TOSA 的降级路径：

.. mermaid::

   flowchart LR
       A[TOSA] --> B[linalg]
       B --> C[scf]
       C --> D[LLVM Dialect]
       D --> E[LLVM IR]

与 StableHLO 的对比
=========================

.. list-table:: TOSA vs StableHLO
   :header-rows: 1

   * - 特性
     - TOSA
     - StableHLO
   * - 设计目标
     - 推理部署
     - 训练和推理
   * - 操作集大小
     - 较小（~50 个操作）
     - 较大（~100+ 个操作）
   * - 量化支持
     - 原生支持
     - 通过 custom call
   * - 动态形状
     - 不支持
     - 支持
   * - 版本稳定性
     - 高度稳定
     - 版本化演进
   * - 主要应用
     - Arm 后端、嵌入式
     - TensorFlow、JAX、PyTorch

源码走读：TOSA 的 ODS 定义
================================

TOSA Dialect 的操作定义在
`TosaOpBase.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Tosa/IR/TosaOpBase.td>`__ 。
其设计强调**推理部署**——操作集小而稳定，每个 Op 的 ``summary`` 和
``description`` 都明确标注了量化支持和形状约束。

TOSA 到 linalg 的降级 Pass 位于 ``mlir/lib/Conversion/TosaToLinalg/`` ，
这使得 TOSA 可以接入 :ref:`mlir-11-06-02` 描述的标准 tensor → scf 管道，
而不需要为 TOSA 单独实现到底层的降级。

动手验证
==========

观察 TOSA 降级管道中共享的后半段，用项目 linalg 示例模拟：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/tensor_add.mlir \
       --one-shot-bufferize=bufferize-function-boundaries \
       --convert-linalg-to-loops

TOSA 前端降到 linalg 后，走的就是这条路径。

本章小结
========

TOSA 面向推理部署，StableHLO 面向训练灵活性，两者通过降级管道在 linalg 层汇合。
下一节 :ref:`mlir-11-07-02` 深入 StableHLO 的版本化设计。
