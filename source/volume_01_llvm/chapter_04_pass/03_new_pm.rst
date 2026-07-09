.. _chapter-04-03-new-pm:

==========================
New Pass Manager
==========================

上一节我们看到了 Legacy PM 的种种问题。LLVM 社区从 2016 年左右开始设计
**New Pass Manager** （New PM），并在 LLVM 15（2022 年）将其设为默认。

.. rst-class:: center

   如果说 Legacy PM 是一个"能用的原型"，那 New PM 就是一个"产品级的设计"。

.. admonition:: New PM 的"分析失效"机制
   :class: note

   Legacy PM 最大的隐患是：变换 Pass 修改了 IR，但分析 Pass 的缓存结果
   没有失效，导致后续 Pass 基于过时的信息做决策。

   New PM 用 **PreservedAnalyses** 解决这个问题——每个 Pass 必须声明
   "我保留了哪些分析结果"。如果 ``InstCombine`` 说"Dominance 分析仍然有效"，
   后续 Pass 就可以复用缓存；如果说"全部失效"，框架自动重算。

   这个设计让 Pass 组合变得安全：`clang -O2` 运行的几十个 Pass
   能正确共享分析结果，同时避免不必要的重算。LLVM 15 将 New PM 设为
   默认，正是因为这一机制已经足够成熟。

New PM 的设计动机
====================

New PM 要解决的核心问题：

1. **类型安全** — 分析结果的类型在编译期确定，不再需要运行时 ``cast``
2. **高效缓存** — 分析结果自动缓存，Pass 管理器跟踪哪些分析仍然有效
3. **透明的失效机制** — 变换 Pass 明确声明它"保留"了哪些分析结果
4. **线程安全** — 支持并发执行不同 Function 的 Pass
5. **明确的管道定义** — 用 ``PassBuilder`` 取代了宏注册

New PM 的核心接口
====================

New PM 不再使用继承体系（不再有 ``FunctionPass`` 基类），而是使用 **CRTP mixin** ：

.. code-block:: cpp
   :caption: llvm/include/llvm/IR/PassManager.h

   // 变换 Pass 的接口
   struct MyTransformPass : public PassInfoMixin<MyTransformPass> {
       // 核心方法：运行 Pass
       PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM);
   };

   // 分析 Pass 的接口
   struct MyAnalysisPass : public AnalysisInfoMixin<MyAnalysisPass> {
       // 核心方法：运行分析
       MyResult run(Function &F, FunctionAnalysisManager &AM);
       // 唯一的分析 ID
       static AnalysisKey Key;
   };

对比 Legacy PM，**不再有 return bool** （是否修改 IR），而是返回
``PreservedAnalyses``——一个显式声明"我保留了哪些分析结果"的集合。

PreservedAnalyses 机制
==========================

这是 New PM 最精妙的设计之一。当变换 Pass 执行完后，它需要告诉管理器：

.. code-block:: cpp

   PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM) {
       // ... 修改 IR ...

       // 情况 1：没有修改 IR → 所有分析结果都有效
       return PreservedAnalyses::all();

       // 情况 2：只修改了指令，没有修改 CFG
       auto PA = PreservedAnalyses::all();
       PA.abandon<DominatorTreeAnalysis>();  // DT 可能变了
       return PA;

       // 情况 3：大幅修改了 IR → 所有分析都失效
       return PreservedAnalyses::none();
   }

管理器根据返回的 ``PreservedAnalyses`` 决定哪些分析结果可以缓存重用。
这比 Legacy PM 的 `setPreservesCFG()` 更加细粒度和精确。

完整的 New PM Pass 示例
============================

下面是一个完整的 New PM Pass，它统计每个函数的指令数
（与上一节 Legacy PM 版本对比）：

.. code-block:: cpp

   #include "llvm/IR/PassManager.h"
   #include "llvm/IR/Function.h"
   #include "llvm/IR/BasicBlock.h"
   #include "llvm/Support/raw_ostream.h"
   using namespace llvm;

   struct InstCountPass : public PassInfoMixin<InstCountPass> {
       PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM) {
           int Count = 0;
           for (BasicBlock &BB : F) {
               Count += BB.size();
           }
           outs() << "Function: " << F.getName()
                  << " has " << Count << " instructions\n";
           // 没有修改 IR → 保留所有分析结果
           return PreservedAnalyses::all();
       }
   };

注意：**不需要 ID** ，**不需要 RegisterPass 宏** ，**不需要匿名命名空间** 。
代码简洁了很多。

分析 Pass 的编写
====================

分析 Pass 需要额外定义一个 **Key** 和 **Result** ：

.. code-block:: cpp

   // 分析结果：某函数中的指令数量
   struct InstCountResult {
       int Count;
   };

   // 分析 Pass
   struct InstCountAnalysis : public AnalysisInfoMixin<InstCountAnalysis> {
       // Key：全局唯一，标识这个分析
       static AnalysisKey Key;

       // 运行分析，返回结果
       InstCountResult run(Function &F, FunctionAnalysisManager &AM) {
           int Count = 0;
           for (BasicBlock &BB : F) Count += BB.size();
           return {Count};
       }
   };

   AnalysisKey InstCountAnalysis::Key;

使用分析结果：

.. code-block:: cpp

   PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM) {
       // 直接获取结果，类型安全
       const auto &Result = AM.getResult<InstCountAnalysis>(F);
       outs() << "Instruction count: " << Result.Count << "\n";
       return PreservedAnalyses::all();
   }

New PM 的管道定义：PassBuilder
===================================

New PM 使用 ``PassBuilder`` 来构建优化管道，不再需要 ``RegisterPass`` 宏：

.. code-block:: cpp

   PassBuilder PB;
   FunctionPassManager FPM;

   // 手动构建管道
   FPM.addPass(InstCountPass());
   FPM.addPass(Mem2RegPass());

   // 用 -passes 命令行接口
   // 在 opt 中：-passes='inst-count,mem2reg'

.. code-block:: console

   # 运行自定义 Pass（New PM）
   $ opt -load-pass-plugin=./libInstCountPass.so \
         -passes='inst-count,mem2reg' input.ll

``-load-pass-plugin`` 对应 New PM 的 Pass 插件加载方式，
这与 Legacy PM 的 ``-load`` 不同。New PM 的插件使用 ``llvm::PassPlugin`` 接口：

.. code-block:: cpp

   extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo
   llvmGetPassPluginInfo() {
       return {
           LLVM_PLUGIN_API_VERSION, "InstCountPass", "v0.1",
           [](PassBuilder &PB) {
               PB.registerPipelineParsingCallback(
                   [](StringRef Name, FunctionPassManager &FPM,
                      ArrayRef<PassBuilder::PipelineElement>) {
                       if (Name == "inst-count") {
                           FPM.addPass(InstCountPass());
                           return true;
                       }
                       return false;
                   });
           }};
   }

Legacy PM vs New PM 对比
============================

.. list-table::
   :header-rows: 1

   * - 特征
     - Legacy PM
     - New PM
   * - 引入时间
     - LLVM 1.0（2003）
     - LLVM 6（2018，实验性质）
   * - 默认启用
     - 直到 LLVM 14
     - 从 LLVM 15 起
   * - Pass 注册
     - ``RegisterPass<>`` 宏
     - ``PassPlugin`` + ``PassBuilder``
   * - 命令行选项
     - ``-pass-name``
     - ``-passes='name'``
   * - 类型安全
     - 无（需运行时 cast）
     - 有（编译期模板参数）
   * - 分析缓存
     - 无
     - 有（自动管理）
   * - 线程安全
     - 否
     - 是
   * - 多 Pass 管道
     - 通过命令行拼接
     - ``PassBuilder`` 显式构建

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
