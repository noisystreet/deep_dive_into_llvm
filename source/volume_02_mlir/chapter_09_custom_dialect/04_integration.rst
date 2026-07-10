.. _mlir-09-09-04:

=====================
自定义 mlir-opt 集成
=====================

开发完 Dialect 后，最后一步是将其集成到 ``mlir-opt`` 中，使其能够
参与 MLIR 的编译管道。

.. rst-class:: center

   ``mlir-opt`` 的集成 = 注册 Dialect + 注册 Pass + 集成到 CMake。

.. admonition:: toyc.cpp：从玩具编译器到生产工具的模板
   :class: tip

   Toy Tutorial Ch7 的 ``toyc.cpp`` 把 Dialect 注册、Pass Pipeline、
   文件 I/O 封装为一个独立编译器——这是自定义 Dialect 走向实用的
   标准路径。IREE 的 ``iree-compile`` 、Buddy 的 ``buddy-opt``
   都遵循同一骨架：

   1. ``registerDialect<MyDSL>()``
   2. ``registerPass<...>()``
   3. ``MlirOptMain`` 或自定义 ``main()``

   你不必 fork ``mlir-opt`` 源码——在自己的工具中链接 MLIR 库、
   注册 Dialect 和 Pass 即可。CMake 中 ``add_mlir_library`` 和
   ``mlir_tablegen`` 宏帮你处理代码生成依赖。

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

与 Toy Tutorial 的集成对照
================================

MyDSL 的 ``mydsl-opt`` 集成模式与 Toy Ch7 的 ``toyc.cpp`` 完全对应。
Toy 编译器入口在
`toyc.cpp <file:///workspace/llvm-project/mlir/examples/toy/Ch7/toyc.cpp>`__ ，
其核心流程：

.. code-block:: text

   1. 注册 Dialect（Toy + Func + LLVM 等）
   2. 构建 PassManager，添加降级 Pipeline
   3. pm.run(module) 执行管道
   4. ExecutionEngine::create(module) 创建 JIT
   5. engine->invoke("main") 执行

MyDSL 的 ``mydsl-opt`` 只覆盖前两步——它是**开发调试工具** ；
Toy 的 ``toyc`` 则覆盖全部五步，是**端到端编译器** 。

源码走读：MlirOptMain
================================

``mlir-opt`` 的入口函数是 ``MlirOptMain`` ，定义在
`MlirOptMain.h <file:///workspace/llvm-project/mlir/include/mlir/Tools/mlir-opt/MlirOptMain.h>`__ 。
官方 ``mlir-opt`` 工具在
`mlir-opt.cpp <file:///workspace/llvm-project/mlir/tools/mlir-opt/mlir-opt.cpp>`__
中调用它，传入 ``DialectRegistry`` 和已注册的 Pass。

自定义 ``mydsl-opt`` 只需多做两件事：

1. ``registry.insert<MyDSLDialect>()`` 注册自定义 Dialect
2. ``PassPipelineRegistration`` 注册自定义 Pass

其余命令行解析、Pass 调度、IR 验证全部由 ``MlirOptMain`` 处理——
这与第一卷 :ref:`chapter-09-01-opt` 中 ``opt`` 工具的架构完全类比。

源码走读：Toy Ch7 的 JIT 集成
================================

Toy Ch7 在降级后调用 ``ExecutionEngine`` 执行程序，详见
:ref:`mlir-11-11-04` 中对 ``ExecutionEngine.h`` 的分析。
``toyc.cpp`` 中的关键代码：

.. code-block:: cpp

   auto engine = mlir::ExecutionEngine::create(module);
   if (!engine) return ...;
   auto error = engine->invoke("main");

将 MyDSL 扩展到可执行编译器，只需在 ``mydsl-opt`` 管道之后
接上 ``mlir-translate`` + ``ExecutionEngine`` ，或直接使用 ``mlir-cpu-runner`` 。

动手验证
==========

用项目示例走通等价的端到端管道：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts \
     | mlir-translate --mlir-to-llvmir

这条命令等价于 ``mydsl-opt`` 完成降级后接 ``mlir-translate`` 的效果。
项目 CI 通过 ``scripts/verify-mlir-examples.sh`` 自动验证所有 ``examples/mlir/`` 示例。

本章小结
========

自定义 Dialect 开发的最后一步是**工具集成** ：注册 Dialect 和 Pass，
让用户能通过命令行驱动编译管道。MyDSL 的 ``mydsl-opt`` 是最小集成；
Toy 的 ``toyc`` 是完整编译器。掌握前者是理解后者的基础。

第二卷至此完结。附录 :ref:`mlir-appendix` 提供了源码阅读指南和 Dialect 速查表，
供后续深入时查阅。


.. rubric:: 进一步阅读

- `CIRCT 项目 <https://circt.llvm.org/>`_ — 基于 MLIR 的硬件设计工具
- `IREE: MLIR 的端到端应用 <https://iree.dev/>`_ — 完整的 MLIR 编译管道
- :ref:`第 9 章 MyDSL 设计 <mlir-09-09-01>` — MyDSL 的设计思路参考


*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
