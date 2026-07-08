.. _mlir-07-07-04:

=================
MLIR-GPU 代码生成
=================

MLIR-GPU 是 MLIR 中用于 GPU 代码生成的子系统。它提供了一组可以映射到
CUDA、ROCm 和 OpenCL 后端的 Dialect 和 Pass。

.. rst-class:: center

   MLIR-GPU 的目标：写一次 Dialect 程序，生成到多个 GPU 后端。

GPU Dialect
===================

MLIR 的 GPU Dialect 提供了**与后端无关**的 GPU 编程抽象：

**启动配置**

.. code-block:: text

   // GPU 启动配置
   gpu.launch_func @kernel
       blocks = (%bx, %by, %bz) in (%grid_x, %grid_y, %grid_z_x)
       threads = (%tx, %ty, %tz) in (%block_x, %block_y, %block_z_z)

**内置变量**

.. code-block:: text

   %block_id = gpu.block_id  x          // blockIdx.x
   %thread_id = gpu.thread_id  x        // threadIdx.x
   %grid_dim = gpu.grid_dim  x          // gridDim.x
   %block_dim = gpu.block_dim  x        // blockDim.x

**内存操作**

.. code-block:: text

   // 共享内存
   %shared = gpu.shared_memory  : memref<256xf32, 3>

   // 全局内存
   gpu.global_id  x  // 全局线程 ID

GPU 的降级路径
=========================

.. mermaid::

   flowchart LR
       A[linalg/tensor] --> B[gpu.launch]
       B --> C[gpu Dialect + NVIDIA Dialect]
       C --> D[LLVM Dialect + NVVM Dialect]
       D --> E[LLVM IR]
       E --> F[PTX]

**NVIDIA (CUDA) 路径**

.. code-block:: console

   $ mlir-opt \
       --convert-linalg-to-gpu \
       --gpu-kernel-outlining \
       --convert-gpu-to-nvvm \
       --convert-nvvm-to-llvm \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       input.mlir | mlir-translate --mlir-to-llvmir

**AMD (ROCm) 路径**

.. code-block:: console

   $ mlir-opt \
       --convert-linalg-to-gpu \
       --gpu-kernel-outlining \
       --convert-gpu-to-rocdl \
       --convert-rocdl-to-llvm \
       input.mlir | mlir-translate --mlir-to-llvmir

Kernel Outlining
======================

``gpu-kernel-outlining`` Pass 从 GPU Launch 操作中提取 kernel 函数：

.. code-block:: text

   // outlining 前
   gpu.launch_func @main_kernel, blocks=(...), threads=(...) {
       // kernel 代码内嵌在 launch 内
       gpu.return
   }

   // outlining 后：kernel 被提取为独立的函数
   func.func @main_kernel(%arg0: memref<1024xf32>) {
       // kernel 代码
       gpu.return
   }

NVIDIA 特有操作（NVVM Dialect）
===============================

当降级到 NVIDIA 后端时，MLIR 生成 NVVM Dialect，它包含了 PTX 的特定操作：

.. code-block:: text

   // CUDA 特有的操作
   nvvm.read.ptx.sreg.tid.x : i32        // threadIdx.x
   nvvm.read.ptx.sreg.ctaid.x : i32      // blockIdx.x
   nvvm.read.ptx.sreg.ntid.x : i32       // blockDim.x
   nvvm.read.ptx.sreg.nctaid.x : i32     // gridDim.x

   // 同步与内存
   nvvm.barrier                           // __syncthreads()
   nvvm.shfl.sync.bfly %val, %mask : f32 // warp shuffle

mlir-gpu-runner
========================

``mlir-gpu-runner`` 类似于 ``mlir-cpu-runner``，但使用 GPU：

.. code-block:: console

   $ mlir-opt --convert-linalg-to-gpu \
       --gpu-kernel-outlining \
       --convert-gpu-to-nvvm \
       --convert-nvvm-to-llvm \
       input.mlir \
       | mlir-gpu-runner -e main -entry-point-result=f32 \
           --shared-libs=libmlir_cuda_runtime.so

在 GPU 上运行 MLIR 程序的完整流程：

.. code-block:: console

   # 1. MLIR 程序 → GPU Dialect
   # 2. GPU Dialect → NVVM Dialect
   # 3. NVVM Dialect → LLVM IR + 设备代码（PTX）
   # 4. JIT 编译 + 执行

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
