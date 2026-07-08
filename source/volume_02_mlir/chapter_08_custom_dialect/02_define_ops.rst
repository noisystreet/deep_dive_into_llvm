.. _mlir-08-08-02:

=====================
定义 Operation
=====================

本节使用 ODS（Operation Definition Spec）定义 MyDSL 的两个 Operation：
``mac`` 和 ``square``。

.. rst-class:: center

   ODS 定义 = 告诉 MLIR 你的 Operation 长什么样。剩下的代码由
   ``mlir-tblgen`` 自动生成。

ODS 定义文件
====================

``MyDSLOps.td``：

.. code-block:: text

   // MyDSLOps.td
   include "mlir/IR/OpBase.td"
   include "mydsl/MyDSLDialect.td"

   // MAC Op：multiply-accumulate（d = a * b + c）
   def MacOp : Op<MyDSL_Dialect, "mac"> {
       let summary = "Multiply-accumulate operation";
       let description = [{
           Performs d = a * b + c.
           All operands and the result have the same integer type.
       }];

       let arguments = (ins
           SignlessIntegerLike:$a,
           SignlessIntegerLike:$b,
           SignlessIntegerLike:$c
       );

       let results = (outs SignlessIntegerLike:$result);

       let assemblyFormat =
           "$a `,` $b `,` $c attr-dict `:` type($result)";

       // 验证：操作数必须为整数
       let verifier = [{
           if (!getA().getType().isSignlessInteger() ||
               !getB().getType().isSignlessInteger() ||
               !getC().getType().isSignlessInteger())
               return emitOpError("operands must be signless integers");
           if (getA().getType() != getB().getType() ||
               getA().getType() != getC().getType())
               return emitOpError("all operands must have the same type");
           return success();
       }];

       // 规范化和常量折叠
       let hasCanonicalizer = 1;
   }

   // Square Op：平方（result = x * x）
   def SquareOp : Op<MyDSL_Dialect, "square"> {
       let summary = "Square operation";
       let description = [{
           Computes result = x * x.
       }];

       let arguments = (ins SignlessIntegerLike:$x);
       let results = (outs SignlessIntegerLike:$result);

       let assemblyFormat = "$x attr-dict `:` type($result)";

       let verifier = [{
           if (!getX().getType().isSignlessInteger())
               return emitOpError("operand must be a signless integer");
           return success();
       }];

       let hasCanonicalizer = 1;
   }

生成的 C++ 访问器
========================

``mlir-tblgen -gen-op-defs`` 为 ``MacOp`` 生成的代码：

.. code-block:: cpp

   class MacOp : public Op<MacOp> {
   public:
       using Op::Op;
       static StringRef getOperationName() { return "my_dsl.mac"; }

       // 参数访问器
       Value getA() { return getOperand(0); }
       Value getB() { return getOperand(1); }
       Value getC() { return getOperand(2); }
       Value getResult() { return getResult(0); }

       // 静态工厂
       static MacOp create(Location loc, Value a, Value b, Value c);

       // 解析/打印
       static ParseResult parse(OpAsmParser &parser,
                                OperationState &result);
       void print(OpAsmPrinter &p);

       // 验证
       LogicalResult verify();
   };

Dialect 注册
====================

``MyDSLDialect.cpp``：

.. code-block:: cpp

   #include "mydsl/MyDSLDialect.h"
   #include "mydsl/MyDSLOps.h"

   void MyDSLDialect::initialize() {
       // 注册 Operation
       addOperations<MacOp, SquareOp>();
   }

CMake 配置
====================

.. code-block:: cmake

   # CMakeLists.txt
   set(LLVM_TARGET_DEFINITIONS MyDSLOps.td)
   mlir_tablegen(MyDSLOps.h.inc -gen-op-defs)
   mlir_tablegen(MyDSLOps.cpp.inc -gen-op-defs)
   add_public_tablegen_target(MyDSLOpsTableGen)

   add_mlir_library(MyDSL
       MyDSLDialect.cpp
       MyDSLOps.cpp

       DEPENDS
       MyDSLOpsTableGen
   )

使用 MyDSL
====================

定义完成后，就可以在 MLIR 中使用：

.. code-block:: console

   $ cat > test.mlir << EOF
   func.func @test(%a: i32, %b: i32) -> i32 {
       %0 = my_dsl.mac %a, %b, %a : i32
       %1 = my_dsl.square %0 : i32
       func.return %1 : i32
   }
   EOF

   # 用 mlir-opt 验证
   $ mlir-opt --allow-unregistered-dialect test.mlir

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
