.. _mlir-11-09-02:

===================
mlir-translate
===================

``mlir-translate`` 负责 MLIR 与其他格式之间的 **双向翻译** 。它最常用于
将 MLIR 的 LLVM Dialect 翻译为标准的 LLVM IR（`.ll` 文件）。

.. rst-class:: center

   ``mlir-translate`` 与 ``mlir-opt`` 的分工：
   ``mlir-opt`` 做 Dialect 间转换， ``mlir-translate`` 做格式间翻译。

.. admonition:: mlir-opt 与 mlir-translate 的分工边界
   :class: note

   新手常混淆这两个工具：

   - **mlir-opt** — IR 到 IR，输入输出都是 ``.mlir`` 。做 Dialect 转换、
     优化、分析。类比 LLVM 的 ``opt`` 。
   - **mlir-translate** — IR 到外部格式。最常见是 ``--mlir-to-llvmir`` ，
     也支持 SPIR-V、LLVM IR 回译为 MLIR 等。类比没有直接对应——
     最接近 ``llvm-dis`` 的逆操作。

   记忆口诀： **opt 改内容，translate 改格式** 。完整管道通常是
   ``mlir-opt ... | mlir-translate --mlir-to-llvmir`` 。

基本用法
==============

.. code-block:: console

   # MLIR → LLVM IR
   $ mlir-translate --mlir-to-llvmir input_llvm.mlir -o output.ll

   # LLVM IR → MLIR
   $ mlir-translate --llvmir-to-mlir input.ll -o output.mlir

支持的翻译
==================

.. list-table:: mlir-translate 支持的翻译
   :header-rows: 1

   * - 方向
     - 选项
     - 说明
   * - MLIR → LLVM IR
     - ``--mlir-to-llvmir``
     - 最常用的翻译
   * - LLVM IR → MLIR
     - ``--llvmir-to-mlir``
     - 导入 LLVM IR 到 MLIR
   * - MLIR → LLVM Bitcode
     - ``--mlir-to-llvmbc``
     - 二进制 LLVM IR
   * - MLIR Bytecode → MLIR
     - ``--bytecode-to-mlir``
     - MLIR 序列化格式
   * - StableHLO → MLIR
     - ``--serialize`` / ``--deserialize``
     - StableHLO 的格式
   * - GPU 相关
     - ``--mlir-to-gpu-binary``
     - GPU 二进制

MLIR → LLVM IR 翻译
========================

.. code-block:: console

   # 标准用法
   $ mlir-opt \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --convert-memref-to-llvm \
       input.mlir \
       | mlir-translate --mlir-to-llvmir -o output.ll

   # 然后可以用 LLVM 工具链继续处理
   $ opt -O2 output.ll -o output_opt.ll
   $ llc -filetype=obj output_opt.ll -o output.o

LLVM IR → MLIR 导入
=========================

.. code-block:: console

   $ mlir-translate --llvmir-to-mlir input.ll -o output.mlir

这个功能主要用于：将现有的 LLVM IR 程序导入 MLIR 环境进行进一步转换。
通常在迁移场景中使用。

StableHLO 序列化
======================

.. code-block:: console

   # 序列化：MLIR → MLIR Bytecode
   $ stablehlo-translate --serialize model.mlir -o model.mlirbc

   # 反序列化：MLIR Bytecode → MLIR
   $ stablehlo-translate --deserialize model.mlirbc -o model.mlir

MLIR Bytecode 格式比文本格式更紧凑，适合生产环境部署。

翻译 Pipeline 的组成
======================

``mlir-translate --mlir-to-llvmir`` 内部的翻译流程：

.. code-block:: cpp

   // 内部调用 ModuleTranslation
   // 1. 遍历 MLIR ModuleOp 中的所有 Operation
   // 2. 对于每个 op，调用对应的翻译函数
   // 3. 生成 llvm::Module
   // 4. 打印为 LLVM IR 文本

注册自定义翻译
==================

.. code-block:: cpp

   // 注册从自定义 Dialect 到 LLVM IR 的翻译
   mlir::TranslateFromMLIRRegistration reg(
       "my-dialect-to-llvmir",
       "Convert MyDSL to LLVM IR",
       [](mlir::ModuleOp module, llvm::raw_ostream &os) {
           // 自定义翻译逻辑
           return mlir::success();
       },
       [](mlir::DialectRegistry &registry) {
           registry.insert<MyDSLDialect>();
       });

源码走读：ModuleTranslation
================================

``--mlir-to-llvmir`` 通道的核心是
`ModuleTranslation.cpp <file:///workspace/llvm-project/mlir/lib/Target/LLVMIR/ModuleTranslation.cpp>`__ 。
文件头注释：

.. code-block:: text

   This file implements the translation between an MLIR LLVM dialect module and
   the corresponding LLVMIR module.

翻译器遍历 MLIR Module 中的 LLVM Dialect Operation，逐一生成
``llvm::Instruction`` 。生成的 ``llvm::Module`` 可交给第一卷介绍的
``opt`` 和 ``llc`` 继续处理——详见 :ref:`chapter-09-02-llc` 。

动手验证
==========

用项目示例走通 MLIR → LLVM IR 翻译：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-translate --mlir-to-llvmir

输出应包含 ``define i32 @add`` 。可将结果保存为 ``.ll`` 文件，
再用 ``opt -S`` 查看优化后的 IR。

本章小结
========

``mlir-translate`` 是 MLIR 降级管道的最后一环翻译工具，将 LLVM Dialect 固化为
标准 LLVM IR。它与 ``mlir-opt`` 配合，完成从 MLIR 到机器码的衔接。
