.. _chapter-05-06-interprocedural-opt:

==============================
过程间优化（IPO）
==============================

前面的所有优化都是**函数内部** 的。它们只分析单个函数，无法跨越函数边界。
过程间优化（Interprocedural Optimization, IPO）突破了这一限制，
在**整个编译单元甚至整个程序** 的范围内做优化。

.. rst-class:: center

   函数内的优化像是在一个房间里整理东西，IPO 则是打通墙壁、重新布置整栋楼。

IPO 的优势与挑战
====================

**优势：**

- **更大的分析范围** ：可以看到调用者和被调用者的上下文
- **更精确的信息** ：可以推导出函数参数的实际取值范围
- **全局优化** ：消除从未被调用的函数、从未被使用的全局变量

**挑战：**

- **编译时间** ：整个程序的分析比单个函数慢得多
- **链接器集成** ：需要链接器配合（LTO/ThinLTO）
- **保守性** ：如果缺少某些调用点的信息，必须做保守假设

全局死函数消除（GlobalDCE）
===============================

``GlobalDCE`` 删除整个程序中从未被调用（或调用已被内联消除）的函数。

.. code-block:: llvm

   ; 输入：foo 从未被调用
   define void @foo() { ... }   ; 永远不会被执行
   define void @bar() { call void @baz(); }

   ; 输出：foo 被删除，bar 保留
   define void @bar() { call void @baz(); }

这个 Pass 很少引起注意，但它能显著减少输出文件的大小。特别是当模板元编程
或代码生成产生了大量从未使用的函数时。

在源码中的位置：`llvm/lib/Transforms/IPO/GlobalDCE.cpp <file:///workspace/llvm-project/llvm/lib/Transforms/IPO/GlobalDCE.cpp>`__

死全局变量消除（DeadGlobalElimination）
===========================================

与 GlobalDCE 类似，但针对全局变量。如果全局变量从未被读取，它会被删除。

.. code-block:: llvm

   @unused_constant = constant i32 42  ; 从未被使用
   @used_constant = constant i32 10   ; 被 load

   define i32 @get() {
       %v = load i32, ptr @used_constant
       ret i32 %v
   }

经过 DeadGlobalElimination：

.. code-block:: llvm

   @used_constant = constant i32 10

   define i32 @get() {
       %v = load i32, ptr @used_constant
       ret i32 %v
   }

``@unused_constant`` 被删除了。注意：如果全局变量以 ``volatile`` 标记，
或者有 `used` 属性（防止优化的标记），它们会被保留。

函数特化（Function Specialization）
=========================================

函数特化根据特定的调用上下文生成函数的专门版本。

.. code-block:: c

   // 原函数
   int compute(int a, int flag) {
       if (flag) return a * 2;
       return a * 3;
   }

   // 如果多数调用点传递 flag=1
   int compute_default(int a, int flag) {  // 原函数保留
       if (flag) return a * 2;
       return a * 3;
   }

   int compute_flag1(int a) {               // 特化版本
       return a * 2;                         // flag 分支被消除
   }

函数特化后，内联 Pass 可以更容易地将特化版本的函数体内联到调用点。
因为特化版本更小、更简单。

参数推广（ArgumentPromotion）
=================================

将**指针参数** 替换为**值参数** ，从而减少内存访问、增加优化机会。

.. code-block:: c

   // 优化前：通过指针传递（promotion 前）
   // 生成的 IR 包含 load/store
   int compute(struct Point *p) {
       return p->x + p->y;
   }

   // 调用者
   int r = compute(&pt);

   // 优化后：直接传值（promotion 后）
   // 生成的 IR：add i32 %x, %y
   int compute(int x, int y) {
       return x + y;
   }

   // 调用者
   int r = compute(pt.x, pt.y);

参数推广的前提是：指针指向的对象没有别名访问，且在函数内外没有副作用。
这需要别名分析（AliasAnalysis）来验证。

全局变量内部化（Global Internalization）
=============================================

将具有外部链接的全局变量或函数改为内部链接（``internal`` ），
如果它们在当前编译单元之外没有被引用。

.. code-block:: llvm

   ; 优化前
   @global_var = global i32 42     ; 默认 external

   ; 优化后（如果外部没有引用）
   @global_var = internal global i32 42  ; 变为 internal

内部化后，优化器得以做更激进的优化——因为知道这个符号不会被外部代码访问，
可以安全地删除或修改它。

ThinLTO 中的 IPO
====================

传统的全程序 IPO（Full LTO）虽然优化效果好，但代价是**将整个程序合并到一个
Module 中分析** ，这会导致极长的链接时间和巨大的内存消耗。

**ThinLTO** 是 LLVM 对 LTO 的可扩展性改进：

.. mermaid::

   flowchart LR
       subgraph 编译阶段（并行）
           A[foo.c → foo.bc] --> D[生成摘要信息]
           B[bar.c → bar.bc] --> D
           C[baz.c → baz.bc] --> D
       end
       subgraph 索引阶段
           D --> E[读取所有摘要]
           E --> F[为每个 Module 计算\n需要导入的函数]
       end
       subgraph 后端阶段（并行）
           F --> G[foo 优化 + 代码生成]
           F --> H[bar 优化 + 代码生成]
           F --> I[baz 优化 + 代码生成]
       end

ThinLTO 的核心思想：**不合并 IR，只合并摘要信息** 。

每个编译单元生成一个**摘要** （包含函数参数、全局变量引用等信息，但不包含
函数体），然后根据摘要为每个 Module 计算需要导入的函数，最后并行地做优化和
代码生成。这样既获得了跨模块优化的收益，又保持了并行构建的优势。

在源码中的位置：`llvm/lib/LTO/ <file:///workspace/llvm-project/llvm/lib/LTO/>`__

.. rubric:: 进一步阅读

- `LLVM 优化通道文档 <https://llvm.org/docs/Passes.html>`_ — 每个优化 Pass 的详细说明
- `Vectorization 指南 <https://llvm.org/docs/Vectorizers.html>`_ — LLVM 的循环和 SLP 向量化
- Steven Muchnick 的 *Advanced Compiler Design and Implementation* — 经典优化教科书


--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
