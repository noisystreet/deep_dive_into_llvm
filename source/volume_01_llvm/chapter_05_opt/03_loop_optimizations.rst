.. _chapter-05-03-loop-optimizations:

======================
循环优化
======================

循环是程序中计算密度最高的区域，也是编译器优化收益最大的地方。LLVM 有一整套
专门针对循环的优化 Pass。

.. rst-class:: center

   大多数程序的运行时间花在循环上。优化循环 = 优化性能。

.. admonition:: 循环优化为何是"编译器的圣杯"
   :class: note

   Aho 等人在《编译原理》中指出：循环是科学计算和系统软件中
   最主要的性能瓶颈。LLVM 的循环优化 Pass 形成了一条"流水线"：

   1. **LICM** — 把不变量提到循环外
   2. **IndVarSimplify** — 简化归纳变量，为向量化铺路
   3. **LoopRotate** — 旋转循环，暴露更多优化机会
   4. **LoopVectorize** — 生成 SIMD 指令

   这条流水线的设计哲学是 **逐层暴露结构**——每步为下一步创造条件。
   理解循环优化，就理解了 LLVM 如何将"数学上的迭代"转化为"硬件上的并行"。

LoopInfo 与 ScalarEvolution
===============================

循环优化的基础是两个分析 Pass：

- ``LoopInfo`` ：识别 CFG 中的自然循环，提供循环的结构信息（上节已介绍）
- **ScalarEvolution** （SCEV）：对循环内整数表达式进行闭式分析，推导归纳变量的变化规律

.. code-block:: cpp

   // 给一个循环归纳变量 i，SCEV 能推导出它的取值范围和变化步长
   // for (int i = 0; i < n; i++)  →  SCEV: {0,+,1}<loop>
   // for (int i = 0; i < n; i+=2) →  SCEV: {0,+,2}<loop>

SCEV 的分析结果（ ``SCEVAddRecExpr`` ）是大多数循环优化的数学基础。

循环不变量外提（LICM）
==========================

LICM（Loop Invariant Code Motion）将循环内 **不随迭代变化的计算** 外提到循环前。

.. code-block:: c

   // 优化前：每次迭代都重复计算
   for (int i = 0; i < n; i++) {
       a[i] = a[i] * (b + c);  // b + c 是循环不变量
   }

   // 优化后：外提到循环前
   int t = b + c;
   for (int i = 0; i < n; i++) {
       a[i] = a[i] * t;
   }

在 LLVM IR 层面，LICM 做的操作是：

1. 识别循环内哪些指令的 **所有操作数都不受循环控制** （即 SCEV 分析结果为常量或不变）
2. 将这些指令通过 ``moveToPreheader`` 移出循环

.. code-block:: llvm

   ; LICM 前
   for.body:
       %t = add i32 %b, %i       ; 不是不变量（依赖 %i）
       %v = add i32 %x, %y       ; 是不变量（可以外提）
       store i32 %v, ptr %arr
       br i1 %cond, label %for.body, label %for.end

   ; LICM 后
   for.preheader:
       %v = add i32 %x, %y       ; 被外提到循环前
   for.body:
       %t = add i32 %b, %i       ; 仍然在循环内
       store i32 %v, ptr %arr
       br i1 %cond, label %for.body, label %for.end

LICM 的源码位置：`llvm/lib/Transforms/Scalar/LICM.cpp <file:///workspace/llvm-project/llvm/lib/Transforms/Scalar/LICM.cpp>`__

归纳变量简化（IndVarSimplify）
=================================

归纳变量（Induction Variable）是循环中每次迭代按固定步长变化的变量。
``IndVarSimplify`` Pass 将各种归纳变量规范化为从 0 开始、步长为 1 的标准形式。

.. code-block:: c

   // 优化前：从 1 到 100，步长 2
   for (int i = 1; i <= 100; i += 2) { ... }

   // 优化后（IndVarSimplify 内部处理）
   for (int i = 0; i < 50; i++) {
       int original_i = 1 + i * 2;  // 用规范归纳变量计算原值
       ...
   }

规范化后的归纳变量更易于 SCEV 分析和后续优化（如循环展开、向量化）。

在源码中的位置：`llvm/lib/Transforms/Scalar/IndVarSimplify.cpp <file:///workspace/llvm-project/llvm/lib/Transforms/Scalar/IndVarSimplify.cpp>`__

循环展开（Loop Unrolling）
==============================

循环展开将循环体复制多份，减少循环控制指令（ ``br`` 、 ``icmp`` ）的执行次数。

.. code-block:: c

   // 展开前
   for (int i = 0; i < 8; i++) {
       a[i] = a[i] * 2;
   }

   // 展开 4 次后（unroll factor = 4）
   for (int i = 0; i < 8; i += 4) {
       a[i]   = a[i]   * 2;  // 第 1 次
       a[i+1] = a[i+1] * 2;  // 第 2 次
       a[i+2] = a[i+2] * 2;  // 第 3 次
       a[i+3] = a[i+3] * 2;  // 第 4 次
   }

再进一步，如果迭代次数在编译期已知，可以 **完全展开** ：

.. code-block:: c

   // 完全展开（full unroll）
   a[0] = a[0] * 2;
   a[1] = a[1] * 2;
   // ... 循环控制逻辑被完全消除

LLVM 有两个展开相关的 Pass：

- ``LoopFullUnroll`` ：完全展开编译期已知迭代次数的循环
- ``LoopUnroll`` ：按指定因子部分展开

展开决策也依赖于代价模型——展开会增大代码体积，需要在性能和大小之间权衡。

循环融合与分发
====================

**循环融合** （Loop Fusion）：将多个独立但可合并的循环合并为一个。

.. code-block:: c

   // 融合前：两个循环访问同一数组
   for (int i = 0; i < n; i++) a[i] = b[i] * 2;
   for (int i = 0; i < n; i++) c[i] = a[i] + 1;

   // 融合后
   for (int i = 0; i < n; i++) {
       a[i] = b[i] * 2;
       c[i] = a[i] + 1;
   }

融合的好处：减少循环开销， **提高数据局部性** （a 的写入后立即被读取）。

**循环分发** （Loop Distribution）：和融合相反——将一个包含多条依赖路径的循环
拆分为多个小循环，以便后续向量化。

循环强度削减（Loop Strength Reduction）
===========================================

将循环内耗费大的运算替换为耗费小的运算。

.. code-block:: c

   // 强度削减前：在循环内计算地址偏移
   char *p = base;
   for (int i = 0; i < n; i++) {
       use(p + i * 20);  // i * 20 是乘法
   }

   // 强度削减后：用加法替代乘法
   char *p = base;
   for (int i = 0; i < n; i++) {
       use(p);
       p += 20;          // 加法比乘法快
   }

LLVM 的 ``LoopStrengthReduce`` Pass 专门做这件事。它特别善于处理数组索引和
地址计算中的乘法表达式。

调试循环优化
================

.. code-block:: console

   # 查看 LICM 做了什么
   $ opt -passes='licm' -debug-only=licm input.ll -S 2>&1

   # 查看循环展开
   $ opt -passes='loop-unroll' -debug-only=loop-unroll input.ll -S 2>&1

   # 禁用循环优化
   $ clang -O2 -fno-loop-optimizations ...

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
