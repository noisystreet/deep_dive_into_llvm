.. _chapter-04-02-legacy-pm:

==========================
Legacy Pass Manager
==========================

在讲 New Pass Manager 之前，有必要先了解 Legacy Pass Manager——虽然它已被标记为弃用，
但 LLVM 生态中仍有大量代码基于它构建，理解它的设计有助于你更好地理解 New PM 的改进。

.. rst-class:: center

   Legacy PM 是 LLVM 最早的 Pass 框架，从 2003 年 LLVM 诞生起一直用到 LLVM 14。
   2022 年，LLVM 15 正式将 New PM 设为默认。

Legacy PM 的设计
====================

Legacy PM 的核心继承体系是这样的：

.. code-block:: text

   Pass
   ├── ModulePass      # 在整个 Module 上运行
   ├── FunctionPass    # 在每个 Function 上运行
   ├── BasicBlockPass  # 在每个 BasicBlock 上运行
   └── LoopPass        # 在每个 Loop 上运行

每个 Pass 继承自其中一个基类，并实现对应的 ``run`` 方法：

.. code-block:: cpp

   class MyLegacyPass : public FunctionPass {
   public:
       // Pass 的唯一标识，用于命令行注册和运行时识别
       static char ID;

       MyLegacyPass() : FunctionPass(ID) {}

       // 核心方法：对每个 Function 执行
       bool runOnFunction(Function &F) override {
           // 在这里分析或修改 F
           // 返回值：true 表示 IR 被修改，false 表示未修改
           return false;
       }
   };

   // 定义 Pass ID
   char MyLegacyPass::ID = 0;

Pass 的注册与命令行集成
============================

Legacy Pass 需要用宏注册，这样 ``opt`` 才能通过命令行找到它：

.. code-block:: cpp

   // 注册 Pass（让 opt -my-pass 可用）
   static RegisterPass<MyLegacyPass> X("my-pass",
       "My First Legacy Pass");

完整的 Legacy Pass 示例
============================

下面是一个完整的 Legacy Pass，它的作用是统计每个函数中的指令数：

.. code-block:: cpp

   #include "llvm/Pass.h"
   #include "llvm/IR/Function.h"
   #include "llvm/IR/Instruction.h"
   #include "llvm/Support/raw_ostream.h"
   using namespace llvm;

   namespace {
       struct InstCountPass : public FunctionPass {
           static char ID;
           InstCountPass() : FunctionPass(ID) {}

           bool runOnFunction(Function &F) override {
               int Count = 0;
               for (BasicBlock &BB : F) {
                   Count += BB.size();  // BB.size() 返回指令数
               }
               errs() << "Function: " << F.getName()
                      << " has " << Count << " instructions\n";
               return false;  // 没有修改 IR
           }
       };
   }

   char InstCountPass::ID = 0;
   static RegisterPass<InstCountPass> X("inst-count",
       "Count instructions per function");

编译并运行：

.. code-block:: console

   # 假设编译成了 shared library
   $ opt -load ./libInstCountPass.so -inst-count input.ll -S -o /dev/null
   Function: add has 12 instructions
   Function: main has 8 instructions

获取分析结果：getAnalysisUsage
================================

如果一个变换 Pass 需要依赖分析 Pass 的结果，Legacy PM 要求你在
``getAnalysisUsage`` 中声明依赖：

.. code-block:: cpp

   bool runOnFunction(Function &F) override {
       // 获取 DominatorTree 分析结果
       auto &DT = getAnalysis<DominatorTreeWrapperPass>().getDomTree();
       // DT 现在可用...
       return false;
   }

   void getAnalysisUsage(AnalysisUsage &AU) const override {
       // 声明需要 DominatorTree
       AU.addRequired<DominatorTreeWrapperPass>();
       // 声明会修改 IR（使某些分析结果失效）
       AU.setPreservesCFG();  // 如果只修改指令不修改 CFG
   }

如果不声明依赖，直接调用 ``getAnalysis`` 会在运行时断言失败。

Legacy PM 的局限性
=====================

Legacy PM 在设计上有几个根本问题，这也是 New PM 被创造出来的原因：

**1. 类型不安全**

``getAnalysis`` 返回的是 ``Pass*`` ，需要手动 ``cast`` 到正确类型：

.. code-block:: cpp

   // Legacy PM：需要 cast
   auto *DT = &getAnalysis<DominatorTreeWrapperPass>().getDomTree();

   // 如果传错了模板参数，编译期不会报错，运行时才崩溃

**2. 分析结果无法高效缓存**

如果三个 Pass 都依赖 ``DominatorTree`` ，Legacy PM 会运行三次分析。
它缺少"分析结果缓存 + 失效标记"的机制。

**3. 无法处理 IR 更新**

当一个 Function Pass 修改 IR 后，Legacy PM 无法通知其他分析 Pass 结果已失效。
Pass 作者需要手动管理——这是很多 bug 的源头。

**4. 线程不安全**

Legacy Pass 是全局单例的，不支持多线程并发执行。在 LLVM 开始支持 JIT 和
并行编译后，这个问题越来越突出。

下一节我们将看到 New PM 如何解决这些问题。
