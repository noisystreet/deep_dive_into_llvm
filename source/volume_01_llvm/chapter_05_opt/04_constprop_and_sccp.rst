.. _chapter-05-04-constprop-and-sccp:

==============================
常量传播与 SCCP
==============================

常量传播是编译器中最经典、最基础的优化之一。它的观察很简单：**如果一个值
在编译期就能确定，那就直接使用它的编译期已知值** 。

.. rst-class:: center

   常量传播把运行时的计算提前到编译时。它本身收益不大，但它为后续优化
   （死代码消除、分支折叠）铺平了道路。

常量折叠 vs 常量传播
============================

两个概念经常被混淆：

.. list-table::
   :header-rows: 1

   * - 概念
     - 做什么
     - 发生时机
   * - **常量折叠** （Constant Folding）
     - 在编译期计算常量表达式的结果
     - 在 LLVM IR 生成的每一阶段
   * - **常量传播** （Constant Propagation）
     - 将变量的值替换为已知常量
     - 在优化 Pass 中

**常量折叠** 的例子：

.. code-block:: text

   ; 编译器直接算出结果
   %v = add i32 3, 4    →    %v = i32 7

``ConstantFold`` 函数在 LLVM 的 IR 构建阶段就会执行，不需要单独的 Pass。
这是 LLVM IRBuilder 中默认开启的行为。

**常量传播** 的例子：

.. code-block:: llvm

   ; 传播前
   %x = add i32 1, 2        ; 实际上 %x = 3
   %y = add i32 %x, %x      ; %y = %x + %x

   ; 传播后
   %x = add i32 1, 2        ; IRBuilder 已折叠为 3
   %y = add i32 3, 3        ; %x 被替换为常量 3

   ; 再经过折叠
   %y = i32 6

SCCP（稀疏条件常量传播）
============================

SCCP（Sparse Conditional Constant Propagation）是常量传播的**更强大版本** 。
它不仅传播常量，还能分析控制流——如果某个分支的条件在编译期就是确定值，
SCCP 可以直接消除死分支。

.. code-block:: c

   int compute(int x, int flag) {
       int y = 0;
       if (flag) {           // 如果 flag 是常量
           y = complex_calc(x);
       } else {
           y = 42;
       }
       return y;
   }

如果 SCCP 发现 ``flag`` 总是 0，它可以简化成：

.. code-block:: c

   int compute(int x, int flag) {
       return 42;            // 整个 else 分支被保留，
                             // if 和 then 分支被消除
   }

SCCP 的工作原理可以用一个**值格** （Value Lattice）来描述：

.. code-block:: text

        undef（未定义）
        /           \
    常量（42）      overdefined（非常量，无法优化）
        \           /
        常量折叠

每个 SSA 值处于以下三种状态之一：

1. **undef** （未定义）：还未被访问到，或者值为 ``undef``
2. **常量** （Constant）：被确定为某个具体常量
3. **overdefined** （非常量）：无法确定为常量（比如函数参数、内存加载值）

SCCP Pass 的工作流程：

1. 初始化所有值为 ``undef``
2. 遍历所有指令，根据操作数的值格状态推导结果的值格状态
3. 如果条件分支的条件是常量，只遍历到达的分支
4. 重复 2-3 直到不再变化（不动点迭代）
5. 将所有标记为常量的 SSA 值替换为实际常量

LLVM 中相关 Pass：

- ``SCCPPass`` ：函数内 SCCP
- ``IPSCCPPass`` （Interprocedural SCCP）：跨越函数边界的 SCCP，能传播参数常量和全局变量常量

GlobalOpt（全局优化）
========================

``GlobalOpt`` Pass 将全局变量的优化做到极致：

.. code-block:: llvm

   ; 优化前
   @G = internal global i32 42

   define i32 @get() {
       %v = load i32, ptr @G
       ret i32 %v
   }

如果 ``@G`` 只被 ``get`` 函数读取，从未被写入：

.. code-block:: llvm

   ; 优化后
   define i32 @get() {
       ret i32 42        ; 直接返回常量
   }

``GlobalOpt`` 还会处理：全局常量传播、全局变量内部化（internalize）、
全局变量的拆分和合并等。

实战：用 opt 观察常量传播
==============================

.. code-block:: console

   $ cat test.ll
   define i32 @test(i32 %x) {
       %a = add i32 10, 32     ; 常量折叠：42
       %b = add i32 %a, %x     ; 传播：%b = 42 + %x
       %c = add i32 %b, 0      ; 恒等：%c = %b
       ret i32 %c
   }

   $ opt -passes='sccp,instcombine' test.ll -S -o -
   define i32 @test(i32 %x) {
       %b = add i32 42, %x     ; 常量折叠 + 传播
       ret i32 %b              ; add 0 被 instcombine 消除
   }

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
