.. _mlir-08-08-04:

=====================
自定义 mlir-opt 集成
=====================

开发完 Dialect 后，最后一步是将其集成到 ``mlir-opt`` 中，使其能够
参与 MLIR 的编译管道。

.. rst-class:: center

   ``mlir-opt`` 的集成 = 注册 Dialect + 注册 Pass + 集成到 CMake。

注册 Dialect
==================

**ODS 注册**

.. code-block:: text

   // MyDSLDialect.td
   def MyDSL_Dialect : Dialect {
       let name = "my_dsl";
       let summary = "My DSL dialect";
       let description = [{
           A simple arithmetic DSL for demonstration.
       }];

       // 依赖的 Dialect
       let dependentDialects = [
           "arith::ArithDialect"
       ];

       // 自动生成初始化代码
       let useDefaultAttributePrinterParser = 1;
       let useDefaultTypePrinterParser = 1;
   }

**C++ 注册**

.. code-block:: cpp

   // MyDSLDialect.cpp
   #include "mydsl/MyDSLDialect.h"
   #include "mydsl/MyDSLOps.h"

   void MyDSLDialect::initialize() {
       addOperations<MacOp, SquareOp>();
   }

   // MyDSLDialect.h
   class MyDSLDialect : public Dialect {
   public:
       explicit MyDSLDialect(MLIRContext *context);
       static StringRef getDialectNamespace() { return "my_dsl"; }
   };

注册 Pass
==================

.. code-block:: cpp

   // MyDSLPasses.h
   #include "mlir/Pass/Pass.h"

   std::unique_ptr<Pass> createConvertMyDSLToArithPass();

   // MyDSLPasses.cpp
   #include "MyDSLPasses.h"
   #include "MyDSLToArith.h"

   std::unique_ptr<Pass> createConvertMyDSLToArithPass() {
       return std::make_unique<ConvertMyDSLToArithPass>();
   }

集成到 mlir-opt
==================

``mlir-opt`` 是 MLIR 的主测试工具。注册 Dialect 和 Pass：

.. code-block:: cpp

   // tools/mydsl-opt/mydsl-opt.cpp
   #include "mydsl/MyDSLDialect.h"
   #include "MyDSLPasses.h"

   int main(int argc, char **argv) {
       mlir::DialectRegistry registry;
       // 注册 MyDSL Dialect
       registry.insert<MyDSLDialect>();
       // 注册 MyDSL Pass
       mlir::PassPipelineRegistration<>(
           "convert-mydsl-to-arith",
           "Convert MyDSL operations to arith dialect",
           [](mlir::OpPassManager &pm) {
               pm.addPass(createConvertMyDSLToArithPass());
           });

       return mlir::MlirOptMain(argc, argv, "MyDSL optimizer",
                                registry);
   }

CMake 配置
==================

.. code-block:: cmake

   # tools/mydsl-opt/CMakeLists.txt
   add_llvm_tool(mydsl-opt
       mydsl-opt.cpp
   )

   target_link_libraries(mydsl-opt PRIVATE
       MyDSL
       MLIRArithDialect
       MLIRFuncDialect
       MLIRPass
       MLIRSupport
       MLIROptLib
   )

使用 mydsl-opt
==================

编译后：

.. code-block:: console

   $ mydsl-opt --convert-mydsl-to-arith test.mlir

   $ mydsl-opt --convert-mydsl-to-arith \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       test.mlir | mlir-translate --mlir-to-llvmir

   # 查看所有 Pass
   $ mydsl-opt --help

端到端验证
==================

.. code-block:: console

   $ cat > test.mlir << EOF
   func.func @test(%a: i32, %b: i32) -> i32 {
       %0 = my_dsl.mac %a, %b, %a : i32
       %1 = my_dsl.square %0 : i32
       func.return %1 : i32
   }
   EOF

   $ mydsl-opt --convert-mydsl-to-arith test.mlir

   // 期望输出：
   func.func @test(%a: i32, %b: i32) -> i32 {
       %0 = arith.muli %a, %b : i32
       %1 = arith.addi %0, %a : i32
       %2 = arith.muli %1, %1 : i32
       func.return %2 : i32
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
