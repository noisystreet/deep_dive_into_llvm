.. _chapter-08-05-custom-jit:

======================
自定义 JIT 实现
======================

前两节我们看了 LLJIT——一个开箱即用的 JIT API。但在实际项目中，你很可能需要
定制化的 JIT 引擎。ORC JIT 的设计就是为了让你能灵活地组合各 Layer。

.. rst-class:: center

   一个典型的自定义 JIT：选择需要的 Layer，配置 IR 优化管道，
   定义符号解析规则，再添加一些自定义功能。

基于 ORC 构建自定义 JIT
=============================

下面是一个完整的自定义 JIT 实现，它支持 IR 优化、符号解析和懒编译：

.. code-block:: cpp

   #include "llvm/ExecutionEngine/Orc/IRCompileLayer.h"
   #include "llvm/ExecutionEngine/Orc/IRTransformLayer.h"
   #include "llvm/ExecutionEngine/Orc/RTDyldObjectLinkingLayer.h"
   #include "llvm/ExecutionEngine/Orc/CompileOnDemandLayer.h"
   #include "llvm/ExecutionEngine/Orc/ExecutionSession.h"
   #include "llvm/ExecutionEngine/Orc/LLJIT.h"
   #include "llvm/ExecutionEngine/SectionMemoryManager.h"
   #include "llvm/IR/Module.h"
   #include "llvm/IR/IRBuilder.h"
   #include "llvm/Support/TargetSelect.h"
   #include "llvm/Target/TargetMachine.h"
   #include "llvm/Transforms/IPO.h"
   #include "llvm/Transforms/Scalar.h"

   using namespace llvm;
   using namespace llvm::orc;

   class MyJIT {
   private:
       ExecutionSession ES;
       RTDyldObjectLinkingLayer ObjLayer;
       IRCompileLayer CompileLayer;
       IRTransformLayer OptimizeLayer;
       JITDylib &MainJD;

   public:
       MyJIT(std::unique_ptr<TargetMachine> TM)
           : ObjLayer(ES, []() {
               return std::make_unique<SectionMemoryManager>();
             }),
             CompileLayer(ObjLayer,
                 std::make_unique<SimpleCompiler>(*TM)),
             OptimizeLayer(CompileLayer,
                 [](std::unique_ptr<Module> M) {
                     // 自定义优化管道
                     auto PM = std::make_unique<FunctionPassManager>();
                     PM->addPass(InstCombinePass());
                     PM->addPass(GVNPass());
                     auto MPM = std::make_unique<ModulePassManager>();
                     MPM->addPass(createModuleToFunctionPassAdaptor(
                         std::move(*PM)));
                     MPM->run(*M, MPM->getResult());
                     return M;
                 }),
             MainJD(ES.createJITDylib("main")) {}

       void addModule(std::unique_ptr<Module> M) {
           // 提交 Module 到主 JITDylib
           cantFail(OptimizeLayer.add(MainJD,
               ThreadSafeModule(std::move(M),
                   std::make_unique<LLVMContext>())));
       }

       Expected<JITEvaluatedSymbol> lookup(StringRef Name) {
           return ES.lookup({&MainJD}, Name);
       }
   };

   int main() {
       // 初始化目标
       InitializeAllTargetInfos();
       InitializeAllTargetMCs();
       InitializeAllAsmPrinters();

       // 创建 TargetMachine
       auto TM = std::unique_ptr<TargetMachine>(
           EngineBuilder().selectTarget());

       // 创建自定义 JIT
       MyJIT JIT(std::move(TM));

       // 创建 Module
       auto M = std::make_unique<Module>("test", *new LLVMContext());
       // ... 构造 IR ...

       // 添加并执行
       JIT.addModule(std::move(M));
       auto Sym = JIT.lookup("add");
       auto *Add = (int (*)(int, int))Sym->getAddress();
       outs() << "Result: " << Add(1, 2) << "\n";

       return 0;
   }

集成自定义 Pass
===================

上面示例中的 ``IRTransformLayer`` 已经展示了如何插入自定义优化。如果你想
在 JIT 中使用自己编写的 LLVM Pass：

.. code-block:: cpp

   auto CustomOptLayer = std::make_unique<IRTransformLayer>(
       *CompileLayer,
       [](std::unique_ptr<Module> M) {
           // 应用自定义 Pass
           ModulePassManager MPM;
           MPM.addPass(MyCustomPass());
           MPM.run(*M, MPM.getResult());
           return M;
       });

与外部符号交互
===================

JIT 编译的代码可能需要调用外部函数（如 ``printf`` 、 ``malloc`` ）。
ORC JIT 通过 ``JITDylib::define`` 来注册外部符号：

.. code-block:: cpp

   // 注册外部函数
   auto &JD = ES.createJITDylib("stdlib");
   JD.define(absoluteSymbols(*orc::SymbolMap{
       {ES.intern("printf"),
        JITEvaluatedSymbol(
            reinterpret_cast<uintptr_t>(&printf),
            JITSymbolFlags::Callable)},
       {ES.intern("malloc"),
        JITEvaluatedSymbol(
            reinterpret_cast<uintptr_t>(&malloc),
            JITSymbolFlags::Callable)},
   }));

   // 让主 JITDylib 可以找到这些符号
   MainJD.addToSearchOrder(&JD);

JIT 的性能调优
===================

**编译线程数**

.. code-block:: cpp

   ES.createThreadPool();
   ES.setDispatchTask(...);  // 使用线程池 dispatch

**内存管理**

ORC JIT 默认使用 ``SectionMemoryManager`` ，每次编译分配新的内存页。
如果需要更高的性能，可以自定义内存管理器以重用已编译代码的内存。

**编译优化等级**

对于 JIT 场景，默认使用 ``-O2`` 可能太慢。通常使用 ``-O1`` 或 ``-O0`` ：

.. code-block:: cpp

   auto TM = EngineBuilder()
       .setOptLevel(CodeGenOpt::Less)  // -O1
       .selectTarget();

实用示例：JIT 实现脚本语言
================================

一个常见的模式是：实现一个简单的解释器/编译型语言，运行时用 LLVM JIT 编译：

.. code-block:: text

   脚本源码
      ↓
   词法/语法分析 → AST
      ↓
   AST → LLVM IR Builder → llvm::Module
      ↓
   LLJIT / ORC JIT → 机器码
      ↓
   调用执行

这个模式在很多项目中得到应用：

- **Julia** ：使用 LLVM JIT 编译 Julia 函数
- **TensorFlow XLA** ：将 TensorFlow 计算图编译为高效机器码
- **Rustc** ：使用 LLVM JIT 执行编译期常量求值（const eval）
- **SQLite** 的实验性引擎：JIT 编译 SQL 查询计划

在源码中的位置
=================

.. code-block:: text

   llvm/examples/OrcV2Examples/   # ORC JIT 示例代码
   llvm/lib/ExecutionEngine/Orc/  # ORC JIT 库实现

LLVM 源码树中的示例目录包含了多个完整可运行的 ORC/JIT 示例，值得研究。

.. rubric:: 进一步阅读

- `ORC JIT 文档 <https://llvm.org/docs/ORCv2.html>`_ — LLVM 的 ORC JIT API 参考
- Lang Hames 在 LLVM Dev Meeting 的系列演讲：*ORC JIT Evolution*
- :ref:`第 10 章 JIT Pipeline <chapter-10-01-lto>` — MLIR 中的 JIT 编译


--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
