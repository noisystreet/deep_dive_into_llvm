.. _chapter-05-02-inlining:

==============
函数内联
==============

函数内联是 LLVM 优化器中最重要、也最有影响力的 Pass 之一。它将一个函数调用
（``call`` 指令）替换为被调用函数的**函数体副本** 。

.. rst-class:: center

   内联的本质：用**代码体积** 交换**执行速度**——省去了函数调用的开销，
   并为后续优化创造更大的视野。

一个简单的例子
==================

.. code-block:: llvm

   ; 内联前
   define i32 @add(i32 %a, i32 %b) {
       %sum = add i32 %a, %b
       ret i32 %sum
   }
   define i32 @caller() {
       %r = call i32 @add(i32 1, i32 2)
       ret i32 %r
   }

经过内联后：

.. code-block:: llvm

   ; 内联后
   define i32 @caller() {
       %sum = add i32 1, 2      ; add 的函数体被直接插入
       ret i32 %sum
   }

这不仅仅是省了一次 ``call``/``ret`` 的开销。更重要的是：**内联打开了后续优化的
可能性** 。在上面的例子中，常量传播可以进一步将 ``%sum = add i32 1, 2``
简化为 ``ret i32 3`` 。

内联的收益与代价
====================

内联不是免费的。LLVM 的 ``Inliner`` Pass 通过**代价模型** （Inline Cost Model）
来权衡是否值得内联一个调用点（call site）。

.. list-table:: 内联的权衡
   :header-rows: 1

   * - 因素
     - 正面（值得内联）
     - 负面（不值得内联）
   * - 目标函数大小
     - 很小的函数（getter、小包装）
     - 很大的函数（会导致代码膨胀）
   * - 调用频率
     - 高频调用（hot call site）
     - 低频调用（cold call site）
   * - 参数信息
     - 实参是常量（触发常量传播）
     - 实参是变量（收益有限）
   * - 函数属性
     - ``alwaysinline`` （强制内联）
     - ``noinline`` （禁止内联）
   * - 调用深度
     - 浅层调用
     - 深层嵌套（可能导致指数级膨胀）

Inline Cost Analysis
========================

LLVM 使用 ``InlineCost`` 分析来量化每个调用点的代价。代价的计算方法：

.. code-block:: cpp

   class InlineCost {
       int Cost;     // 内联的估算代价（指令数）
       int Threshold; // 代价阈值
       // 如果 Cost <= Threshold，则内联
       // 如果 Cost > Threshold，则不内联
   };

阈值的默认值：

.. code-block:: text

   -O1: 内联阈值 = 225
   -O2: 内联阈值 = 225
   -O3: 内联阈值 = 275（更激进）

你可以通过参数调整：

.. code-block:: console

   $ clang -O2 -mllvm -inline-threshold=500 ...

代价的计算基于启发式规则：

- 每个 LLVM 指令的基础代价为 **1**
- ``load``/``store`` 代价为 **2** （涉及内存操作）
- ``call`` 代价为 **15** （被调用者如果也可内联，则递归计算）
- 常量参数的传入可以**减去** ``ConstantHoistCost`` （因为后续优化会简化）
- 被标记为 ``cold`` 的函数分支不计算在内
- GEP 指令不计代价（后续优化可以消除）

内联属性
============

LLVM IR 支持在函数和调用点级别控制内联行为：

.. list-table:: 内联相关函数属性
   :header-rows: 1

   * - 属性
     - 作用
   * - ``alwaysinline``
     - 强制内联（忽略代价模型）
   * - ``noinline``
     - 禁止内联
   * - ``inlinehint``
     - 提示优化器应倾向于内联此函数（权重+15%）
   * - ``minsize``
     - 优化代码体积（显著降低内联阈值）
   * - ``optsize``
     - 优化代码体积（降低内联阈值）

.. code-block:: llvm

   ; 强制内联
   define i32 @add(i32 %a, i32 %b) alwaysinline {
       %sum = add i32 %a, %b
       ret i32 %sum
   }

   ; 禁止内联
   call void @do_not_inline() noinline

递归函数的内联处理
=======================

LLVM 不会真正内联递归函数（因为会导致无限展开）。但有一种特殊处理：
**函数调用自己的情况**——LLVM 可能会将函数体内对自己进行递归调用的路径展开一次，
这叫 **inline a recursive call with unrolling** 。

实际实现中，LLVM 对递归函数的处理是：如果发现递归调用，会在代价模型中
将其视为代价非常高的调用（``InlineCost::getNever()`` ），从而阻止内联。

内联 Pass 的源码位置
========================

.. code-block:: text

   llvm/lib/Analysis/InlineCost.cpp        # 内联代价分析
   llvm/lib/Transforms/IPO/Inliner.cpp     # 内联 Pass 主逻辑
   llvm/lib/Transforms/Utils/InlineFunction.cpp  # 内联操作的底层实现

``InlineFunction`` 是内联的底层实现——它负责将函数体复制到调用点，并重映射
参数和局部变量：

.. code-block:: cpp
   :caption: llvm/lib/Transforms/Utils/InlineFunction.cpp（简化）

   InlineResult InlineFunction(CallBase *CB, InlineFunctionInfo &IFI) {
       Function *Callee = CB->getCalledFunction();
       // 1. 克隆被调用者的所有 basic block
       // 2. 将参数映射到实参
       // 3. 重映射局部变量和标签
       // 4. 处理 alloca 指令（必要时提升到 caller 的入口 block）
       // 5. 处理返回指令（将 ret 替换为 br）
       return InlineResult::success();
   }

查看内联决策日志
====================

LLVM 提供了详细的调试日志来追踪内联决策：

.. code-block:: console

   $ opt -passes='inline' -debug-only=inline input.ll -S 2>&1 | head -20

   Inlining  add  cost=5  threshold=225
     Analyzing caller:  main
     Analyzing call site:  call i32 @add
       Cost: 5, Threshold: 225
       Inlining:  positive

你也可以用 ``-pass-remarks=inline`` 获得更可读的输出：

.. code-block:: console

   $ clang -O2 -Rpass=inline ...

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
