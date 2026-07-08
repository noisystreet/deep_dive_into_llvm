.. _mlir-09-09-01:

============
mlir-opt
============

``mlir-opt`` 是 MLIR 生态中**最核心**的工具。它运行 Pass Pipeline 并输出
转换后的 IR，是所有 MLIR 开发和测试的基础工具。

.. rst-class:: center

   ``mlir-opt`` ≈ MLIR 中的 ``opt``——但它支持多 Dialect 和多 Pass Pipeline。

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

可以基于 ``MlirOptMain`` 构建自己的 ``mydsl-opt``：

.. code-block:: cpp

   #include "mlir/Tools/mlir-opt/MlirOptMain.h"

   int main(int argc, char **argv) {
       mlir::DialectRegistry registry;
       registry.insert<MyDSLDialect>();
       registry.insert<mlir::arith::ArithDialect>();
       return mlir::MlirOptMain(
           argc, argv, "My custom optimizer", registry);
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
