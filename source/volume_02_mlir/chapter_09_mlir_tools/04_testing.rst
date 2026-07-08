.. _mlir-09-09-04:

========================
MLIR 测试与 FileCheck
========================

MLIR 的测试体系基于 LLVM 的 **FileCheck** 工具。FileCheck 通过匹配 IR 输出中
的预期行来验证 Pass 的正确性。

.. rst-class:: center

   MLIR 测试的核心公式：
   ``mlir-opt`` + FileCheck = 可重复、可维护的测试。

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

**常用 CHECK 指令**：

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

当输出顺序不确定时使用 ``CHECK-DAG``：

.. code-block:: text

   // RUN: mlir-opt --pass %s | FileCheck %s

   // CHECK-LABEL: func.func
   // CHECK-DAG: arith.constant 1
   // CHECK-DAG: arith.constant 2
   // ^^ 匹配时忽略顺序

mlir-reduce
==================

``mlir-reduce`` 是 MLIR 的**测试用例缩减工具**。当有测试失败时，
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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
