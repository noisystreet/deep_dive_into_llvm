.. _mlir-04-04-05:

======================
mlir-tblgen 的使用
======================

``mlir-tblgen`` 是 MLIR 的 TableGen 代码生成器。它从 `.td` 文件读取
ODS 定义，然后根据不同的命令行选项生成对应的 C++ 代码。

.. rst-class:: center

   编写完 ``.td`` 文件后，``mlir-tblgen`` 帮你完成剩下的 90% 的代码生成工作。

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
