.. _mlir-09-09-02:

=====================
定义 Operation
=====================

本节使用 ODS（Operation Definition Spec）定义 MyDSL 的两个 Operation：
``mac`` 和 ``square``。

.. rst-class:: center

   ODS 定义 = 告诉 MLIR 你的 Operation 长什么样。剩下的代码由
   ``mlir-tblgen`` 自动生成。

.. admonition:: 从 Toy Ch3 到 MyDSL：ODS 定义的"最小闭环"
   :class: tip

   Toy Tutorial Ch3 用不到 100 行 ODS 定义了完整的 Toy Dialect——
   包括 ``mul``、``constant``、``return`` 等 Op。MyDSL 遵循同一模板：

   1. 写 ``MyDSLOps.td`` 定义 Op
   2. ``mlir-tblgen`` 生成 C++ 类
   3. 注册 Dialect 到 ``MyDSL.cpp``
   4. 用 ``mlir-opt`` 解析/打印验证

   建议读者对照 Toy 的 ``Ops.td`` 阅读本节——两个 Dialect 的
   结构几乎相同，区别只在类型名和操作语义。掌握 Toy 就等于
   掌握了自定义 Dialect 的 80%。

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

与 Toy Tutorial 的 ODS 对照
================================

MyDSL 的 ODS 定义模式与 Toy Tutorial Ch3 完全一致。Toy 的 ``MulOp`` 定义在
`Ops.td <file:///workspace/llvm-project/mlir/examples/toy/Ch3/include/toy/Ops.td>`__ ：

.. code-block:: text

   def MulOp : Toy_Op<"mul", [Pure, SameOperandsAndResultType]> {
     let summary = "Multiplication operation";
     let arguments = (ins F64Tensor:$lhs, F64Tensor:$rhs);
     let results = (outs F64Tensor:$result);
     let assemblyFormat = "$lhs `,` $rhs attr-dict `:` type($lhs)";
   }

对比 MyDSL 的 ``MacOp`` ，差异仅在于操作数和 Trait 不同，ODS 结构完全一致：
``arguments`` 声明输入，``results`` 声明输出，``assemblyFormat`` 定义打印格式。
``mlir-tblgen`` 为两者生成相同模式的 C++ 访问器和验证骨架。

CMake 构建时，TableGen 规则自动调用 ``mlir-tblgen`` ：

.. code-block:: cmake

   mlir_tablegen(MyDSLOps.h.inc -gen-op-decls)
   mlir_tablegen(MyDSLOps.cpp.inc -gen-op-defs)

这与第一卷 :ref:`chapter-06-05-code-generation` 中 ``llvm-tblgen`` 的
CMake 集成方式一脉相承，只是生成器从 ``llvm-tblgen`` 换成了 ``mlir-tblgen`` 。

本章小结
========

ODS 定义是自定义 Dialect 的第一步：用 ``.td`` 文件声明 Operation 的结构，
由 ``mlir-tblgen`` 生成 C++ 样板代码。下一节 :ref:`mlir-09-09-03` 将实现
MyDSL 到 arith 的降级 Pattern 。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
