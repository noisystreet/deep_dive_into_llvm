.. _mlir-04-04-04:

=============================
quant / sparse_tensor Dialect
=============================

``quant`` 和 ``sparse_tensor`` 是两个 **专用领域** 的 Dialect。
它们服务于特定场景，但展示了 MLIR 的 Dialect 机制如何扩展到
完全不同的计算需求。

.. rst-class:: center

   这两个 Dialect 代表了 MLIR 生态的两个方向：
   **降低精度** （量化）和 **利用稀疏性** （稀疏张量）。

quant Dialect
=================

``quant`` Dialect 处理 **量化**——将浮点计算转换为定点或整数计算。
这是推理引擎中的核心技术。

**量化类型**

.. code-block:: text

   // 均匀量化（uniform quantization）
   !quant.uniform<i8:f32, 0.1:128>
   // 含义：scale=0.1, zero_point=128, 存储为 i8，模拟为 f32

   // 按通道量化
   !quant.uniform_per_channel<f32:f32, [
       {scale = [1.0, 0.5, 0.25]},
       {zero_point = [0, 1, 2]}
   ]>

**量化操作**

.. code-block:: text

   // 量化：f32 → i8
   %q = quant.quantize %input : f32 -> !quant.uniform<i8:f32, 0.1:128>

   // 反量化：i8 → f32
   %dq = quant.dequantize %q : !quant.uniform<i8:f32, 0.1:128> -> f32

   // 量化的矩阵乘法
   %result = quant.matmul(%a, %b) {
       input_scales = [0.1, 0.2],
       output_scale = 0.5
   } : (!quant.uniform<i8:f32, 0.1:128>,
        !quant.uniform<i8:f32, 0.2:128>)
     -> !quant.uniform<i8:f32, 0.5:128>

quant Dialect 的降级路径：

.. code-block:: text

   quant → arith（整数运算）
     ↓
   arith → LLVM

sparse_tensor Dialect
============================

``sparse_tensor`` Dialect 处理 **稀疏张量**——大部分元素为零的张量。
通过只存储非零元素来节省内存和计算。

**稀疏张量格式**

.. code-block:: text

   // 定义稀疏编码格式
   #CSR = #sparse_tensor.encoding<{
       lvlTypes = ["dense", "compressed"]
   }>  // 压缩行存储

   #CSC = #sparse_tensor.encoding<{
       lvlTypes = ["compressed", "dense"]
   }>  // 压缩列存储

   // COO（坐标格式）
   #COO = #sparse_tensor.encoding<{
       lvlTypes = ["compressed", "singleton"]
   }>

   // 使用稀疏张量类型
   %sparse : sparse_tensor<1024xf32, #CSR>
   %coo    : sparse_tensor<1024x1024xf32, #COO>

**稀疏张量操作**

.. code-block:: text

   // 从坐标创建稀疏张量
   %s = sparse_tensor.init %values, %indices :
       (tensor<100xf32>, tensor<100xi64>) -> sparse_tensor<1024xf32, #CSR>

   // 稀疏张量加法
   %sum = sparse_tensor.add %a, %b
       : sparse_tensor<1024xf32, #CSR>

   // 转换为密集张量
   %dense = sparse_tensor.convert %s
       : sparse_tensor<1024xf32, #CSR> -> tensor<1024xf32>

sparse_tensor 的编译策略：

.. code-block:: text

   sparse_tensor → linalg + scf（循环展开为稀疏迭代）
       ↓
   linalg + scf → arith + memref
       ↓
   LLVM IR

当循环遍历一个稀疏张量时，编译器会自动生成只遍历非零元素的代码。
这就是"稀疏编译器"的核心价值——**利用数据结构的知识来生成更高效的代码** 。

两个 Dialect 的共性
=========================

quant 和 sparse_tensor 代表了 MLIR 的同一个理念：
**把领域知识编码到类型和操作中，让编译器针对这些知识做优化** 。

.. code-block:: text

   量化类型告诉编译器：这个值只有 8 位精度。
   → 编译器可以生成更短的 SIMD 指令（vpmaddubsw 而非 vfmadd231ps）

   稀疏编码告诉编译器：这个张量大部分元素是零。
   → 编译器只遍历非零元素，插入稀疏感知的内存分配

这两个 Dialect 是 MLIR "开放生态"的最佳证明——如果 LLVM IR 的
"唯一 IR" 设计无法处理量化和稀疏张量，但在 MLIR 中，只需要
一个新的 Dialect 就搞定了。

.. rubric:: 进一步阅读

- `memref Dialect <https://mlir.llvm.org/docs/Dialects/MemRef/>`_ — memref 类型和操作
- `Transform Dialect <https://mlir.llvm.org/docs/Dialects/Transform/>`_ — 元编程 IR 变换
- `Sparse Tensor 文档 <https://mlir.llvm.org/docs/Dialects/SparseTensor/>`_ — 稀疏张量编译
