.. _chapter-04-04-analysis-passes:

==========================
分析 Pass 详解
==========================

上一节我们看了如何编写一个简单的分析 Pass。但 LLVM 自带了数十个内置分析 Pass，
它们构成了整个优化系统的基础设施。理解这些分析 Pass 的作用和使用方式，
是编写高效变换 Pass 的关键。

.. rst-class:: center

   分析 Pass 是变换 Pass 的"眼睛"——没有分析，优化就像蒙着眼睛改代码。

DominatorTree（支配树）
============================

支配树是 LLVM 中最重要的分析之一。它回答了：**对于一个 basic block，
哪些 basic block 是到达它的必经之路？**

**定义**：如果从函数入口到 basic block B 的每条路径都经过 A，则称 A **支配** （dominates）B。

.. code-block:: text

   // CFG（控制流图）：
       [entry]
         |
         v
       [if.then] ←→ [if.else]    // 两个分支
           \           /
            v         v
          [if.end]               // merge 点

   // 支配关系：
   // entry 支配所有 block（它是入口）
   // if.end 被 if.then 和 if.else 支配
   // if.then 不支配 if.else（可以绕过）

支配树在循环优化、代码移动（LICM）、死代码删除等 Pass 中都有广泛使用。

.. code-block:: cpp

   // 使用方式：
   auto &DT = AM.getResult<DominatorTreeAnalysis>(F);
   if (DT.dominates(InstA, InstB)) {
       // InstA 的结果在 InstB 处一定可用
   }

在源码中的位置：`llvm/include/llvm/Analysis/Dominators.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/Analysis/Dominators.h>`__

PostDominatorTree（后支配树）
================================

后支配树是支配树的"反向"版本：**如果从 block B 到函数出口的每条路径都经过 A，
则称 A 后支配（post-dominates）B。**

常用于识别"必然会执行到的代码"——如果某条指令后支配了整个函数，它的执行可以被
安全地移动到函数末尾。

LoopInfo（循环分析）
=========================

``LoopInfo`` 识别 CFG 中的自然循环（natural loops），并提供了循环的层次结构：

.. code-block:: cpp

   auto &LI = AM.getResult<LoopAnalysis>(F);
   for (auto *L : LI) {
       outs() << "Loop header: " << L->getHeader()->getName() << "\n";
       outs() << "  Depth: " << L->getLoopDepth() << "\n";
       outs() << "  Blocks:";
       for (auto *BB : L->blocks())
           outs() << " " << BB->getName();
       outs() << "\n";
   }

``LoopInfo`` 提供的关键信息：

- **Header** （循环头）：循环的入口 basic block，支配循环内的所有 block
- **Latch** （循环尾）：有边回到 header 的 block
- **Preheader** （前导块）：循环外唯一跳入 header 的 block
- **SubLoops** （子循环）：嵌套循环的结构
- **Loop Depth** （循环深度）：嵌套层数

这些信息是 LICM（循环不变量外提）、循环展开、循环向量化等优化的基础。

在源码中的位置：`llvm/include/llvm/Analysis/LoopInfo.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/Analysis/LoopInfo.h>`__

AliasAnalysis（别名分析）
============================

别名分析回答了：**两个指针是否可能指向同一块内存？**

.. code-block:: cpp

   auto &AA = AM.getResult<AAManager>(F);
   MemoryLocation LocA = MemoryLocation::get(InstA);
   MemoryLocation LocB = MemoryLocation::get(InstB);
   AliasResult Result = AA.alias(LocA, LocB);

   switch (Result) {
   case AliasResult::NoAlias:      // 一定不指向同一内存
   case AliasResult::MayAlias:     // 可能指向同一内存
   case AliasResult::MustAlias:    // 一定指向同一内存
   case AliasResult::PartialAlias: // 指向重叠但不完全相同的区域
   }

别名分析是 LLVM 中最复杂的分析问题之一。LLVM 实现了多层别名分析的叠加：

.. code-block:: text

   用户请求 Alias Analysis
           │
           ▼
        AAResults（聚合层）
           │
           ├── BasicAA（基本分析：基于 IR 的显式信息）
           ├── TypeBasedAA（基于 TBAA 元数据）
           ├── ScopedNoAliasAA（基于 noalias 元数据）
           ├── ObjCARCAliasAnalysis（ObjC ARC 相关）
           └── ExternalAA（外部注册的分析）

每层都调用下一层做补充，最终给出精度最高的结果。

在源码中的位置：`llvm/include/llvm/Analysis/AliasAnalysis.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/include/llvm/Analysis/AliasAnalysis.h>`__

ScalarEvolution（标量演化分析）
====================================

ScalarEvolution（SCEV）是 LLVM 中对循环和整数表达式进行**闭式分析**的引擎。
它能推导出循环中的整数变量随迭代次数的变化规律。

.. code-block:: cpp

   auto &SE = AM.getResult<ScalarEvolutionAnalysis>(F);

   // 分析循环中的归纳变量
   const SCEV *S = SE.getSCEV(IndVar);
   if (auto *AddRec = dyn_cast<SCEVAddRecExpr>(S)) {
       outs() << "Start: "  << *AddRec->getStart() << "\n";
       outs() << "Step: "   << *AddRec->getStepRecurrence(SE) << "\n";
       outs() << "Loop: "   << *AddRec->getLoop() << "\n";
   }

``getSCEV`` 能处理的表达式类型包括：

- ``SCEVConstant``：常量
- ``SCEVTruncate/SExt/ZExt``：类型扩展/截断
- ``SCEVAddExpr``：加法表达式
- ``SCEVMulExpr``：乘法表达式
- ``SCEVAddRecExpr``：**加法递推表达式** （循环归纳变量）

对一个循环 ``for (i = 0; i < n; i++)``，``i`` 的 SCEV 表示为：
``{0, +, 1}<loop>``——从 0 开始，每次迭代 +1。

这就是循环优化的数学基础。LoopStrengthReduce、IndVarSimplify 等 Pass
都依赖于 SCEV 提供的信息。

AssumptionCache（假设缓存）
============================

``AssumptionCache`` 跟踪函数中用 ``@llvm.assume`` 内建函数注册的假设。
这些假设为优化器提供"额外信息"，允许更激进的优化。

.. code-block:: llvm

   ; 在 IR 中注册假设
   %cond = icmp sgt i32 %x, 0
   call void @llvm.assume(i1 %cond)
   ; 优化器现在知道 %x > 0

   ; 优化器可以据此做出更精确的分析
   ; 比如 "a / %x" 不需要检查除以零

分析结果的失效与重用
=======================

分析 Pass 的结果可以被缓存，直到变换 Pass 使它们失效。
这是 New PM 的一个重要改进。

.. code-block:: text

   变换 Pass 运行前                变换 Pass 运行后
   ┌─────────────────┐           ┌─────────────────┐
   │ DominatorTree    │  cached   │ DominatorTree    │
   │ 计算结果         │──────────→│ 仍然有效（保留）  │
   │ LoopInfo         │           │ LoopInfo         │
   │ 计算结果         │──────────→│ 已失效（需重算）   │
   └─────────────────┘           └─────────────────┘
          │                              │
          ▼                              ▼
   AM.getResult<...>()         AM.getResult<...>()
   返回缓存结果                      重新计算

失效规则由变换 Pass 返回的 ``PreservedAnalyses`` 决定：
- 如果 Pass 声明保留了某个分析，管理器直接返回缓存
- 如果没有声明保留，下一次 ``getResult`` 会重新计算

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
