.. _mlir-05-05-05:

======================
mlir-tblgen 的使用
======================

``mlir-tblgen`` 是 MLIR 的 TableGen 代码生成器。它从 `.td` 文件读取
ODS 定义，然后根据不同的命令行选项生成对应的 C++ 代码。

.. rst-class:: center

   编写完 ``.td`` 文件后， ``mlir-tblgen`` 帮你完成剩下的 90% 的代码生成工作。

.. admonition:: mlir-tblgen 与 llvm-tblgen：师出同门
   :class: note

   两者共享 TableGen 语言，但生成目标不同：

   - **llvm-tblgen** — 生成指令选择器、寄存器描述、汇编打印器
   - **mlir-tblgen** — 生成 Op 类、Dialect 注册、Type/Attr 类、文档

   一个有趣的历史细节：MLIR 最初复用 ``llvm-tblgen`` 二进制，
   后来才独立出 ``mlir-tblgen`` 以支持 ODS 特有的生成后端
   （ ``-gen-op-decls`` 、 ``-gen-typedef-defs`` 等）。
   如果你熟悉第一卷 TableGen，ODS 的学习曲线会平缓很多——
   语法相同，只是 Record 类和生成目标换了。

基本用法
==============

.. code-block:: console

   # 查看所有可用的生成器
   $ mlir-tblgen --help

   # 生成 Op C++ 类声明
   $ mlir-tblgen -gen-op-defs MyDialect.td -o MyDialect.h.inc

   # 生成 Op C++ 实现
   $ mlir-tblgen -gen-op-defs MyDialect.td -o MyDialect.cpp.inc

   # 生成 Dialect 声明（h.inc）
   $ mlir-tblgen -gen-dialect-decls MyDialect.td -o MyDialectDialect.h.inc

   # 生成 Dialect 实现（cpp.inc）
   $ mlir-tblgen -gen-dialect-defs MyDialect.td -o MyDialectDialect.cpp.inc

在 CMake 中集成
======================

.. code-block:: cmake

   # CMakeLists.txt
   set(LLVM_TARGET_DEFINITIONS MyDialect.td)

   # 生成 Op 定义
   mlir_tablegen(MyDialect.h.inc -gen-op-defs)
   mlir_tablegen(MyDialect.cpp.inc -gen-op-defs)

   # 生成 Dialect 定义
   mlir_tablegen(MyDialectDialect.h.inc -gen-dialect-decls)
   mlir_tablegen(MyDialectDialect.cpp.inc -gen-dialect-defs)

   # 生成 Type/Attribute 定义
   mlir_tablegen(MyDialectTypes.h.inc -gen-typedefs)
   mlir_tablegen(MyDialectTypes.cpp.inc -gen-typedefs)
   mlir_tablegen(MyDialectAttrs.h.inc -gen-attributedefs)

   # 确保在编译时生成
   add_public_tablegen_target(MyDialectTableGen)

然后在使用生成文件的源文件中：

.. code-block:: cpp

   #include "MyDialect.h.inc"
   #include "MyDialectDialect.h.inc"
   #include "MyDialectTypes.h.inc"

常用生成器选项
====================

.. list-table:: mlir-tblgen 常用生成器
   :header-rows: 1

   * - 选项
     - 生成内容
     - 输出文件示例
   * - ``-gen-op-defs``
     - Op 类的声明和实现
     - ``MyOps.h.inc``, ``MyOps.cpp.inc``
   * - ``-gen-dialect-decls``
     - Dialect 类的声明
     - ``MyDialectDialect.h.inc``
   * - ``-gen-dialect-defs``
     - Dialect 类的实现
     - ``MyDialectDialect.cpp.inc``
   * - ``-gen-typedefs``
     - Type 类的声明和实现
     - ``MyTypes.h.inc``, ``MyTypes.cpp.inc``
   * - ``-gen-attributedefs``
     - Attribute 类的声明和实现
     - ``MyAttrs.h.inc``, ``MyAttrs.cpp.inc``
   * - ``-gen-pass-decls``
     - Pass 的声明
     - ``MyPasses.h.inc``
   * - ``-gen-pass-doc``
     - Pass 的文档
     - ``MyPasses.md``

调试生成的文件
====================

.. code-block:: console

   # 查看解析后的 .td 文件内容
   $ mlir-tblgen MyDialect.td -print-records

   # 只生成某个 Operation 的代码
   $ mlir-tblgen -gen-op-defs MyDialect.td -I /path/to/mlir/include

   # 查看文件包含路径
   $ mlir-tblgen MyDialect.td -print-records -I /path/to/mlir/include

   # 生成文档
   $ mlir-tblgen -gen-op-doc MyDialect.td -o MyDialect.md

生成的 C++ 代码示例
========================

假设有以下 ODS 定义：

.. code-block:: text

   def AddOp : Op<MyDialect, "add"> {
       let arguments = (ins I32:$lhs, I32:$rhs);
       let results = (outs I32:$result);
       let assemblyFormat = "$lhs `+` $rhs attr-dict";
   }

``mlir-tblgen -gen-op-defs`` 生成的代码大致如下：

.. code-block:: cpp

   class AddOp : public Op<AddOp> {
   public:
       using Op::Op;
       static StringRef getOperationName() { return "my_dialect.add"; }

       // 参数访问器
       Value getLhs() { return getOperand(0); }
       Value getRhs() { return getOperand(1); }
       Value getResult() { return getResult(0); }

       // 静态工厂方法
       static AddOp create(Location loc, Value lhs, Value rhs);

       // 装配格式解析
       static ParseResult parse(OpAsmParser &parser, OperationState &result);
       void print(OpAsmPrinter &p);

       // 验证器（如果自定义了 verifier）
       LogicalResult verify();
   };

一次构建的完整流程
=======================

.. code-block:: console

   # 1. 创建 ODS 文件
   $ cat > MyDialect.td << EOF
   include "mlir/IR/OpBase.td"
   def MyDialect : Dialect { let name = "my"; }
   def MyOp : Op<MyDialect, "my_op"> {
       let arguments = (ins I32:$input);
       let results = (outs I32:$output);
       let assemblyFormat = "$input attr-dict";
   }
   EOF

   # 2. 生成 C++ 代码
   $ mlir-tblgen -gen-op-defs MyDialect.td -I $(llvm-config --includedir)

   # 3. 创建 C++ 源文件并 include
   $ cat > main.cpp << EOF
   #include "MyDialect.h.inc"
   #include "mlir/IR/BuiltinOps.h"
   // ...
   EOF

   # 4. 编译
   $ clang++ main.cpp $(llvm-config --cxxflags --ldflags --libs)

源码走读：mlir-tblgen 的生成器
================================

``mlir-tblgen`` 是 MLIR 专用的 TableGen 后端，实现位于
`MlirTblgenMain.cpp <file:///workspace/llvm-project/mlir/tools/mlir-tblgen/MlirTblgenMain.cpp>`__ ，
与第一卷
:ref:`chapter-06-05-code-generation` 中的 ``llvm-tblgen`` 一脉相承。

常用生成目标：

.. list-table:: mlir-tblgen 生成目标
   :header-rows: 1

   * - 命令行参数
     - 生成内容
   * - ``-gen-op-decls``
     - Operation 类声明 ``.h.inc``
   * - ``-gen-op-defs``
     - Operation 类实现 ``.cpp.inc``
   * - ``-gen-dialect-decls``
     - Dialect 注册声明
   * - ``-gen-typedef-decls``
     - 自定义 Type 声明
   * - ``-gen-enum-decls``
     - 枚举类型声明

Toy Tutorial 的 CMake 构建自动调用这些生成器——
查看
`Ch3/CMakeLists.txt <file:///workspace/llvm-project/mlir/examples/toy/Ch3/CMakeLists.txt>`__
可以看到完整的集成方式。

动手验证
==========

统计 arith Dialect 的 ODS 规模，感受自动生成的威力：

.. code-block:: console

   wc -l llvm-project/mlir/include/mlir/Dialect/Arith/IR/ArithOps.td

本章小结
========

``mlir-tblgen`` 将 ODS 声明转化为 C++ 代码，是 MLIR 开发工作流的核心工具。
掌握它的生成目标，就掌握了自定义 Dialect 的构建流程。
第 5 章 :ref:`mlir-11-index` 将在此基础上介绍如何用 Pass 变换这些 Operation。


.. rubric:: 进一步阅读

- `ODS 文档 <https://mlir.llvm.org/docs/OpDefinitions/>`_ — MLIR Operation 定义规范
- `mlir-tblgen 文档 <https://mlir.llvm.org/docs/Tablegens/>`_ — 代码生成器参考
- :ref:`第 1 卷 TableGen 章节 <chapter-06-01-tablegen-intro>` — TableGen 语言基础
