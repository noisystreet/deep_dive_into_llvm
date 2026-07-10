.. _chapter-05-05-vectorization:

==============
向量化
==============

向量化是现代 CPU 获得极致性能的关键。它将多个标量操作合并为一个 SIMD（单指令多数据）
操作，让一条指令同时处理多个数据。

.. rst-class:: center

   如果一个循环一次处理一个元素，向量化让它一次处理四个——不增加指令数，
   吞吐量提高四倍。

.. admonition:: SLP vs Loop Vectorize：两种向量化的分工
   :class: note

   LLVM 有两条向量化路径，适用场景不同：

   - **Loop Vectorizer** — 在循环中把标量迭代合并为向量迭代。
     适合 ``for (i) a[i] = b[i] + c[i]`` 这类规则循环。
   - **SLP Vectorizer** — 在基本块内把**相邻的独立标量操作**合并为向量。
     适合循环已展开后的 ``a[0]+b[0]`` 、``a[1]+b[1]`` 等操作。

   两者常配合使用：Loop Vectorizer 先合并迭代，SLP 再合并块内残余。
   ``-Rpass-analysis=loop-vectorize`` 可以打印向量化的决策理由——
   是理解"编译器为何拒绝向量化某循环"的最佳工具。

LLVM 中的向量化有两种主要 Pass：

- **Loop Vectorizer** ：自动将循环体向量化
- **SLP Vectorizer** ：在基本块内寻找可向量化的独立指令序列

Loop Vectorizer（循环向量化）
=================================

Loop Vectorizer 是 LLVM 中最重要的向量化 Pass。它分析循环的迭代空间，
判断是否可以安全地合并迭代。

.. code-block:: c

   // 向量化前：每次迭代处理一个元素
   for (int i = 0; i < n; i++) {
       a[i] = b[i] + c[i];
   }

   // 向量化后（假设 SSE，一次 4 个 32 位整数）：
   for (int i = 0; i < n; i += 4) {
       // 一条 padd 指令代替 4 条 add
       vec_a = load <4 x i32>(&b[i]);
       vec_b = load <4 x i32>(&c[i]);
       vec_c = add <4 x i32>(vec_a, vec_b);
       store <4 x i32>(vec_c, &a[i]);
   }

在 LLVM IR 层面，向量化后的代码使用**向量类型** ：

.. code-block:: llvm

   ; 标量版本
   for.body:
       %i = phi i64 [ 0, %entry ], [ %next, %for.body ]
       %b_elem = getelementptr i32, ptr @b, i64 %i
       %b_val = load i32, ptr %b_elem
       %c_elem = getelementptr i32, ptr @c, i64 %i
       %c_val = load i32, ptr %c_elem
       %sum = add i32 %b_val, %c_val
       store i32 %sum, ptr %a_elem
       %next = add i64 %i, 1
       %done = icmp eq i64 %next, %n
       br i1 %done, label %exit, label %for.body

   ; 向量化版本（向量宽度 = 4）
   for.body:
       %i = phi i64 [ 0, %entry ], [ %next, %for.body ]
       %b_elem = getelementptr i32, ptr @b, i64 %i
       %b_vec = load <4 x i32>, ptr %b_elem
       %c_elem = getelementptr i32, ptr @c, i64 %i
       %c_vec = load <4 x i32>, ptr %c_elem
       %sum_vec = add <4 x i32> %b_vec, %c_vec
       store <4 x i32> %sum_vec, ptr %a_elem
       %next = add i64 %i, 4
       %done = icmp eq i64 %next, %n
       br i1 %done, label %exit, label %for.body

向量化的合法性检查
========================

不是所有循环都能被安全地向量化。Loop Vectorizer 在做向量化之前会检查：

1. **依赖分析** ：迭代之间是否存在数据依赖？如果迭代 i+1 需要迭代 i 的结果，
   则不能向量化
2. **别名分析** ：不同指针是否指向同一内存区域？指针别名可能导致错误的向量化结果
3. **控制流** ：循环体内是否有条件分支？如果有，可能需要"if conversion"预处理
4. **类型宽度** ：目标平台是否支持向量宽度对应的 SIMD 指令？

.. code-block:: c

   // 不可向量化：迭代之间有依赖
   for (int i = 1; i < n; i++) {
       a[i] = a[i-1] + 1;  // 依赖上一轮的结果
   }

   // 可向量化：无依赖
   for (int i = 0; i < n; i++) {
       a[i] = b[i] + c[i];  // 每次迭代独立
   }

向量化失败的原因可以通过 ``-Rpass-missed=loop-vectorize`` 查看：

.. code-block:: console

   $ clang -O3 -Rpass-missed=loop-vectorize test.c -c 2>&1
   test.c:3:5: remark: loop not vectorized: unsafe dependent memory operations in loop
   ...

SLP Vectorizer（超字级并行向量化）
=======================================

SLP（Superword-Level Parallelism）Vectorizer 与 Loop Vectorizer 不同：
它不关注循环迭代间的并行性，而是在**基本块内部** 寻找可向量化的标量指令组。

.. code-block:: c

   // SLP 向量化前
   void add(float *a, float *b, float *c) {
       a[0] = b[0] + c[0];
       a[1] = b[1] + c[1];
       a[2] = b[2] + c[2];
       a[3] = b[3] + c[3];
   }

   // SLP 向量化后
   void add(float *a, float *b, float *c) {
       // 将 4 个独立的加法合并为一条向量加法
       *(<4 x float>*)a = *(<4 x float>*)b + *(<4 x float>*)c;
   }

SLP Vectorizer 通过以下步骤工作：

1. 在基本块中识别同构的指令序列（相同的操作码、兼容的类型）
2. 将这些指令组合成一个向量操作
3. 检查组合后的收益是否超过开销

在源码中的位置：`llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp <file:///workspace/llvm-project/llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp>`__

TargetTransformInfo（TTI）
==============================

向量化的效果高度依赖目标架构。LLVM 通过 ``TargetTransformInfo`` （TTI）来
查询目标平台对不同向量操作的代价：

.. code-block:: cpp

   // 查询目标平台对 <4 x i32> 类型加法的代价
   InstructionCost Cost = TTI.getArithmeticInstrCost(
       Instruction::Add, Type::getInt32Ty(Context),
       Type::getInt32Ty(Context));

   // 查询最大支持的向量宽度
   unsigned MaxWidth = TTI.getRegisterBitWidth(true);
   unsigned VF = TTI.getLoadStoreVecRegBitWidth(0);

不同架构返回不同的值：

- x86 SSE：128 位向量
- x86 AVX2：256 位向量
- x86 AVX-512：512 位向量
- AArch64 NEON：128 位向量
- AArch64 SVE：可变长度向量（128-2048 位）

这也是为什么同一个循环在不同 CPU 上可能产生不同的向量化代码。

向量化调试
==============

.. code-block:: console

   # 开启向量化（默认在 -O3 开启，-O2 不开启）
   $ clang -O2 -fvectorize ...

   # 查看向量化报告
   $ clang -O3 -Rpass=loop-vectorize -Rpass-analysis=loop-vectorize ...

   # 查看向量化后的 IR
   $ clang -O3 -S -emit-llvm test.c -o test.ll

   # 调试向量化失败原因
   $ clang -O3 -fno-vectorize -S -emit-llvm test.c -o test.scalar.ll
   $ clang -O3 -S -emit-llvm test.c -o test.vec.ll
   $ diff test.scalar.ll test.vec.ll

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
