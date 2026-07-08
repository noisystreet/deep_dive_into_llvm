.. _mlir-07-07-01:

============
TOSA Dialect
============

TOSA（Tensor Operator Set Architecture）是 MLIR 中一个**用于推理场景**
的 Dialect。它定义了一组可移植的张量操作，专为边缘设备和推理引擎设计。

.. rst-class:: center

   TOSA 的设计目标：一组稳定的、可预测性能的操作集，适合硬件加速器
   和推理引擎直接消费。

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

---------END *本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
