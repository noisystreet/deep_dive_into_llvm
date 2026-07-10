.. _mlir-11-09-04:

========================
MLIR 测试与 FileCheck
========================

MLIR 的测试体系基于 LLVM 的 **FileCheck** 工具。FileCheck 通过匹配 IR 输出中
的预期行来验证 Pass 的正确性。

.. rst-class:: center

   MLIR 测试的核心公式：
   ``mlir-opt`` + FileCheck = 可重复、可维护的测试。

.. admonition:: MLIR 测试文化：每个 Pass 都有 .mlir 测试文件
   :class: note

   LLVM 用 ``test/`` 目录下成千上万的 ``.ll`` + FileCheck 文件
   守护 Pass 正确性。MLIR 继承了这一传统——``mlir/test/`` 中
   每个 Pass 都有对应的 ``.mlir`` 测试，用 ``// RUN:`` 指令
   声明运行方式。

   自定义 Dialect 应遵循同一规范：为每个 Conversion Pattern 写
   ``CHECK`` 行验证输出 IR。项目 CI 中的 ``verify-mlir-examples.sh``
   是简化版——只验证示例能跑通；生产级 Dialect 需要 FileCheck
   级别的细粒度断言。

FileCheck 基础
==================

FileCheck 在测试文件中嵌入 ``CHECK`` 指令：

.. code-block:: text

   // RUN: mlir-opt --canonicalize %s | FileCheck %s

   // CHECK-LABEL: func.func @test
   func.func @test() -> i32 {
       %0 = arith.constant 0 : i32
       // CHECK: arith.constant 0
       func.return %0 : i32
   }

**常用 CHECK 指令** ：

.. list-table:: FileCheck 指令
   :header-rows: 1

   * - 指令
     - 含义
     - 示例
   * - ``CHECK``
     - 匹配行
     - ``// CHECK: arith.constant``
   * - ``CHECK-LABEL``
     - 标记段落开始
     - ``// CHECK-LABEL: func.func @test``
   * - ``CHECK-NEXT``
     - 匹配下一行的内容
     - ``// CHECK-NEXT: arith.constant 42``
   * - ``CHECK-NOT``
     - 确保不出现
     - ``// CHECK-NOT: my_dsl.mac``
   * - ``CHECK-DAG``
     - 不按顺序匹配
     - ``// CHECK-DAG: arith.addi``
   * - ``CHECK-SAME``
     - 匹配同一行
     - ``// CHECK-SAME: type(i32)``

MLIR 测试示例
==================

**降级测试**

.. code-block:: text

   // RUN: mlir-opt --convert-arith-to-llvm %s | FileCheck %s

   // CHECK-LABEL: func.func @add
   func.func @add(%a: i32, %b: i32) -> i32 {
       %0 = arith.addi %a, %b : i32
       // CHECK: llvm.add
       func.return %0 : i32
   }

   // CHECK-LABEL: func.func @mul
   func.func @mul(%a: i32, %b: i32) -> i32 {
       %0 = arith.muli %a, %b : i32
       // CHECK: llvm.mul
       func.return %0 : i32
   }

**转换测试（Transformation Test）**

.. code-block:: text

   // RUN: mlir-opt --canonicalize %s | FileCheck %s

   // CHECK-LABEL: func.func @fold_add_zero
   func.func @fold_add_zero(%x: i32) -> i32 {
       %c0 = arith.constant 0 : i32
       %0 = arith.addi %x, %c0 : i32
       // CHECK-NEXT: return %arg0
       // CHECK-NOT: arith.addi
       func.return %0 : i32
   }

**运行命令解析**

``RUN:`` 行的格式：

.. code-block:: text

   // RUN: mlir-opt --pass %s | FileCheck %s
   //                       ^^          ^^
   //                %s = 当前文件    %s 再次展开为当前文件

   // 多个 RUN 行
   // RUN: mlir-opt -pass1 %s | FileCheck %s --check-prefix=CHECK1
   // RUN: mlir-opt -pass2 %s | FileCheck %s --check-prefix=CHECK2

使用 CHECK-DAG
====================

当输出顺序不确定时使用 ``CHECK-DAG`` ：

.. code-block:: text

   // RUN: mlir-opt --pass %s | FileCheck %s

   // CHECK-LABEL: func.func
   // CHECK-DAG: arith.constant 1
   // CHECK-DAG: arith.constant 2
   // ^^ 匹配时忽略顺序

mlir-reduce
==================

``mlir-reduce`` 是 MLIR 的 **测试用例缩减工具** 。当有测试失败时，
它自动将 IR 缩减到最小的可重现用例：

.. code-block:: console

   $ mlir-reduce --test=%test_script.sh buggy.mlir

   # 它会不断尝试删除 Operation、简化 IR，
   # 直到找到最小的能触发 bug 的 IR

``mlir-reduce`` 的使用场景：

- Pass 崩溃时的 IR 复现
- 验证器失败的最小用例
- Dialect 转换的正确性检查

FileCheck 最佳实践
============================

1. **总是使用 CHECK-LABEL** 组织测试段落
2. **优先用 CHECK-NEXT** 精确匹配而非 CHECK
3. **避免匹配行号** （行号不稳定）
4. **尽量用具体值** 而非通配符
5. **多个 Run 行** 测试不同的 Pass 组合

源码走读：MLIR 测试基础设施
======================================

MLIR 的测试框架建立在 LLVM 的 ``lit`` 之上。每个测试文件的 ``// RUN:`` 指令
指定运行命令和 FileCheck 验证，与第一卷 :ref:`chapter-09-05-filecheck` 完全一致。

``mlir-reduce`` 的实现在
`mlir/lib/Reducer/ <file:///workspace/llvm-project/mlir/lib/Reducer/>`__ 目录下，
它通过二分删除 Operation 来最小化触发 bug 的 IR——
类似 LLVM 的 ``llvm-reduce`` 。

Toy Tutorial 的每个 Chapter 都包含 ``test/`` 目录下的 ``.mlir`` 测试文件，
是编写 FileCheck 测试的最佳参考。例如 Ch6 的降级测试验证了
``toy.print`` → loop → ``printf`` 的完整路径。

动手验证
==========

对项目示例运行基本 FileCheck 风格的验证：

.. code-block:: console

   # 确认降级输出包含预期指令
   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-arith-to-llvm --convert-func-to-llvm \
       --reconcile-unrealized-casts | grep -c "llvm.add"
   # 应输出 1

   # 运行项目 CI 中的完整示例验证
   bash scripts/verify-mlir-examples.sh

本章小结
========

MLIR 的测试体系与 LLVM 一脉相承：lit + FileCheck 验证 IR 变换，
mlir-reduce 最小化 bug 复现。编写自定义 Dialect 时，应为每个 Pass
和降级路径配套 ``.mlir`` 测试文件。


.. rubric:: 进一步阅读

- `MLIR 测试指南 <https://mlir.llvm.org/docs/TestingGuide/>`_ — MLIR 测试最佳实践
- `mlir-opt 工具 <https://mlir.llvm.org/docs/Tools/mlir-opt/>`_ — 命令行参考
- `mlir-cpu-runner <https://mlir.llvm.org/docs/ExecutionEngine/>`_ — JIT 执行器
