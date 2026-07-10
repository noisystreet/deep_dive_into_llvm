.. _mlir-11-09-01:

============
mlir-opt
============

``mlir-opt`` 是 MLIR 生态中**最核心**的工具。它运行 Pass Pipeline 并输出
转换后的 IR，是所有 MLIR 开发和测试的基础工具。

.. rst-class:: center

   ``mlir-opt`` ≈ MLIR 中的 ``opt``——但它支持多 Dialect 和多 Pass Pipeline。

.. admonition:: mlir-opt 的日常：MLIR 开发者的一天的"瑞士军刀"
   :class: tip

   对于一个 MLIR 开发者来说，``mlir-opt`` 就像瑞士军刀一样不可或缺。
   以下是几个真实的使用场景：

   **场景 1：验证降级的正确性**
   开发了一个新的 Dialect 降级模式后：
   ``mlir-opt --convert-my-dialect-to-arith input.mlir``
   一行命令就能看到降级结果。

   **场景 2：调试 Pass 间的影响**
   ``mlir-opt --mlir-print-ir-after-all --pass-pipeline="builtin.module(canonicalize,cse)" input.mlir``
   这里 ``--mlir-print-ir-after-all`` 是 MLIR 调试的神器——
   每一步 Pass 之后都会 dump IR。

   **场景 3：IR 合法性检查**
   ``mlir-opt --verify-each --pass-pipeline="builtin.module(canonicalize,convert-scf-to-cf)" input.mlir``
   每个 Pass 后都会运行验证器——这类似于 LLVM 中 ``opt -verify`` ，
   但因为 MLIR 支持多 Dialect，验证器也支持多 Dialect 的合法性检查。

   **场景 4：测试精简**
   ``mlir-reduce`` 可以从一个数千行的 MLIR 程序中自动缩减到最小可以
   触发 bug 的 IR。这对于复现和报告 bug 非常有帮助。

   可以说，任何 MLIR 开发工作 90% 的时间都离不开 ``mlir-opt`` 。

基本用法
==============

.. code-block:: console

   # 应用 canonicalization Pass
   $ mlir-opt --canonicalize input.mlir

   # 应用多个 Pass
   $ mlir-opt --canonicalize --cse --convert-scf-to-cf input.mlir

   # 使用 Pass Pipeline 字符串
   $ mlir-opt --pass-pipeline="builtin.module(canonicalize,cse)" input.mlir

常用选项
==============

.. code-block:: console

   # IR 打印相关
   --mlir-print-ir-before=cse        # 在 CSE Pass 前打印 IR
   --mlir-print-ir-after=canonicalize # 在 canonicalize Pass 后打印 IR
   --mlir-print-ir-after-all         # 在所有 Pass 后打印 IR

   # 调试
   --mlir-disable-threading          # 禁用多线程（方便调试）
   --debug                           # 开启调试输出

   # 验证
   --verify-each                     # 每个 Pass 后运行验证器

   # 输出
   -o output.mlir                    # 输出到文件
   --mlir-print-op-generic           # 使用通用打印格式

IR 打印示例
==================

.. code-block:: console

   $ mlir-opt --canonicalize --mlir-print-ir-after=canonicalize input.mlir

   // 输出：
   // === Canonicalizer (canonicalize) ===
   // module {
   //   ...
   // }

使用 --debug 分析 Pass
===============================

.. code-block:: console

   $ mlir-opt --debug --pass-pipeline="builtin.module(canonicalize,cse)" \
       input.mlir 2>&1 | head -50

``--debug`` 会输出每个 Pattern 的匹配尝试和结果。

Pass Pipeline 的高级用法
===============================

**动态 Pass 加载**

.. code-block:: console

   $ mlir-opt --load-pass-plugin=/path/to/libMyPass.so \
       --my-pass input.mlir

**嵌套 Pipeline**

.. code-block:: console

   $ mlir-opt \
       --pass-pipeline="builtin.module(
           canonicalize,
           func.func(cse),
           convert-scf-to-cf
       )" input.mlir

**测试重放**

.. code-block:: console

   # 从崩溃日志生成重放脚本
   --pass-pipeline-crash-reproducer

验证模式
==============

``mlir-opt`` 支持两种验证模式来检查 IR 在不同 Pass 前后的结果：

.. code-block:: console

   # 严格模式
   --verify-each                    # 每个 Pass 后都验证

   # 宽松模式
   --mlir-pass-pipeline-crash-reproducer  # 失败时生成重放

自定义 mlir-opt
==================

可以基于 ``MlirOptMain`` 构建自己的 ``mydsl-opt`` ：

.. code-block:: cpp

   #include "mlir/Tools/mlir-opt/MlirOptMain.h"

   int main(int argc, char **argv) {
       mlir::DialectRegistry registry;
       registry.insert<MyDSLDialect>();
       registry.insert<mlir::arith::ArithDialect>();
       return mlir::MlirOptMain(
           argc, argv, "My custom optimizer", registry);
   }

源码走读：mlir-opt 的实现
================================

官方 ``mlir-opt`` 源码在
`mlir-opt.cpp <file:///workspace/llvm-project/mlir/tools/mlir-opt/mlir-opt.cpp>`__ 。
它调用 ``MlirOptMain`` （`MlirOptMain.h <file:///workspace/llvm-project/mlir/include/mlir/Tools/mlir-opt/MlirOptMain.h>`__），
完成三件事：

1. 通过 ``registerAllPasses()`` 注册所有内置 Pass
2. 解析 ``--pass-pipeline`` 或单个 ``--pass-name`` 参数
3. 构建 PassManager 并运行

这与第一卷 :ref:`chapter-09-01-opt` 中的 LLVM ``opt`` 工具形成直接对照——
``opt`` 操作 ``llvm::Module`` ，``mlir-opt`` 操作 ``mlir::Operation`` 。

动手验证
==========

验证项目示例可通过标准 mlir-opt 管道：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir --help | head -5
   bash scripts/verify-mlir-examples.sh

本章小结
========

``mlir-opt`` 是 MLIR 开发者的核心工具，所有 Pass 开发和降级调试都从这里开始。
下一节 :ref:`mlir-11-09-02` 介绍其搭档工具 ``mlir-translate`` 。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
