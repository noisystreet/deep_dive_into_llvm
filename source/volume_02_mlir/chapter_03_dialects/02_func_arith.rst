.. _mlir-03-03-02:

===========================
func / arith / math Dialect
===========================

这三个 Dialect 是 MLIR 中最常用的"中层" Dialect。它们构成了大多数 MLIR
程序的核心骨架：**func** 定义函数结构，**arith** 提供整数运算，**math** 提供数学函数。

.. rst-class:: center

   ``arith`` 和 ``func`` 是 MLIR 中最稳定的 Dialect 之一——几乎所有
   需要降级到 LLVM 的 MLIR 程序都会经过它们。

.. admonition:: arith 为何从 std 独立出来？
   :class: note

   早期 MLIR 把整数运算放在 ``std`` Dialect 中。随着生态扩张，
   ``std`` 变得臃肿且语义模糊——它既管控制流又管算术又管内存。
   2020 年前后的大重构将其拆分为 ``arith`` 、``memref`` 、``scf`` 等
   专职 Dialect。

   ``arith`` 的设计原则是**最小且纯** ：只提供基本算术，附加
   ``Pure`` Trait 标记无副作用，让 CSE/DCE 可以自由优化。
   几乎所有降级管道的倒数第二步都是 ``convert-arith-to-llvm``——
   理解 arith 就是理解 MLIR 到 LLVM 的"最后一公里"前的通用层。

func Dialect
=================

``func`` Dialect 提供了函数定义和调用的机制。它是 MLIR 结构化编程的基础。

**func.func**

.. code-block:: text

   // 定义函数
   func.func @add(%a: i32, %b: i32) -> i32 {
       %r = arith.addi %a, %b : i32
       func.return %r : i32
   }

   // 定义函数（无返回值）
   func.func @print() {
       // ...
       func.return
   }

**func.call**

.. code-block:: text

   // 调用函数
   func.func @main() -> i32 {
       %result = func.call @add(%arg0, %arg1) : (i32, i32) -> i32
       func.return %result : i32
   }

``func.call`` 使用符号引用（``@add`` ）来标识调用目标。MLIR 的符号系统
保证了函数名的唯一性。

func Dialect 的属性：

.. code-block:: text

   // 函数可以带属性
   func.func @inline_me() -> i32 attributes {passthrough = ["alwaysinline"]} {
       %c = arith.constant 42 : i32
       func.return %c : i32
   }

arith Dialect
===================

``arith`` Dialect 提供了标量算术运算。它是 MLIR 中最重要的底层 Dialect 之一。

**整数运算**

.. code-block:: text

   %sum = arith.addi %a, %b : i32         // 整数加法
   %diff = arith.subi %a, %b : i32        // 整数减法
   %prod = arith.muli %a, %b : i32        // 整数乘法
   %quot = arith.divsi %a, %b : i32       // 整数除法（有符号）
   %rem = arith.remsi %a, %b : i32        // 整数取模（有符号）

**浮点运算**

.. code-block:: text

   %sum = arith.addf %a, %b : f32         // 浮点加法
   %diff = arith.subf %a, %b : f32        // 浮点减法
   %prod = arith.mulf %a, %b : f32        // 浮点乘法

**比较运算**

.. code-block:: text

   %cond = arith.cmpi eq, %a, %b : i32    // 整数相等比较
   %cond = arith.cmpi slt, %a, %b : i32   // 有符号小于
   %cond = arith.cmpf olt, %a, %b : f32   // 浮点小于

**类型转换**

.. code-block:: text

   %ext = arith.extsi %a : i32 to i64     // 符号扩展
   %trunc = arith.trunci %a : i64 to i32  // 截断
   %fp = arith.sitofp %a : i32 to f64     // 整数 → 浮点
   %int = arith.fptosi %a : f64 to i32    // 浮点 → 整数

**常量定义**

.. code-block:: text

   %c0 = arith.constant 0 : i32           // 整数常量
   %pi = arith.constant 3.14159 : f64     // 浮点常量
   %true = arith.constant true             // 布尔常量

math Dialect
==================

``math`` Dialect 提供了数学函数。它们通常会被降级为 LLVM 的内建函数调用
（如 ``llvm.sqrt`` 、``llvm.sin`` 等）。

.. code-block:: text

   %r1 = math.sqrt %a : f32               // 平方根
   %r2 = math.powf %a, %b : f32           // 幂运算
   %r3 = math.sin %a : f32                // 正弦
   %r4 = math.cos %a : f32                // 余弦
   %r5 = math.exp %a : f32                // 指数
   %r6 = math.log %a : f32                // 自然对数
   %r7 = math.abs %a : f32                // 绝对值
   %r8 = math.floor %a : f32              // 向下取整
   %r9 = math.ceil %a : f32               // 向上取整
   %r10 = math.atan2 %a, %b : f32         // 双参数反正切

这些数学函数的好处在于：它们在不同的后端目标上可能映射为不同的实现。
在 GPU 上，``math.sqrt`` 可能映射为硬件 ``sqrt`` 指令；在 CPU 上可能
映射为 libm 的 ``sqrt`` 函数。

类型转换与 arith 的关系
==============================

``arith`` 只处理**标量类型（scalar types）**——即 ``i1`` 、``i32`` 、``f32``
等基础类型。如果你需要操作张量（如 ``tensor<4xf32>`` ），需要结合其他 Dialect
（如 ``tensor`` 、``linalg`` ）的 Operation。

.. code-block:: text

   // arith 操作的是标量：
   %sum = arith.addi %a, %b : i32

   // 张量级别的加法需要 tensor 或 linalg：
   %t_sum = linalg.add %t1, %t2 : tensor<4xf32>

从 func → LLVM 的降级路径
================================

.. code-block:: text

   func.func / func.call
         ↓（降级）
   llvm.func / llvm.call
         ↓（翻译）
   LLVM IR: define / call

   arith.addi / arith.constant
         ↓（降级）
   llvm.addi / llvm.mlir.constant
         ↓（翻译）
   LLVM IR: add / constant

源码走读：ODS 中的 Dialect 定义
======================================

三个 Dialect 的 Operation 都通过 ODS 声明。以 ``func.call`` 为例，
`FuncOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Func/IR/FuncOps.td>`__
中的描述：

.. code-block:: text

   def CallOp : Func_Op<"call",
       [CallOpInterface, MemRefsNormalizable,
        DeclareOpInterfaceMethods<SymbolUserOpInterface>]> {
     let summary = "call operation";
     let description = [{
       The `func.call` operation represents a direct call to a function that is
       within the same symbol scope as the call.
     }];

``CallOpInterface`` 和 ``SymbolUserOpInterface`` 是 MLIR 的 Interface 机制——
Pass 可以通过 Interface 统一处理所有"函数调用"语义的 Op，而不必逐个匹配
``func.call`` 、``llvm.call`` 等具体名称。Interface 的详细机制见 :ref:`mlir-05-05-03` 。

``arith`` Dialect 的基类定义在
`ArithOps.td <file:///workspace/llvm-project/mlir/include/mlir/Dialect/Arith/IR/ArithOps.td>`__ ：

.. code-block:: text

   class Arith_Op<string mnemonic, list<Trait> traits = []> :
       Op<Arith_Dialect, mnemonic,
          traits # [..., NoMemoryEffect] # ElementwiseMappable.traits>;

``NoMemoryEffect`` 告诉优化器这些操作没有副作用，可以自由 CSE 和 DCE；
``ElementwiseMappable`` 则允许 arith 操作直接作用于 tensor/vector 的逐元素映射。
这两个 Trait 是 arith 能被广泛重用的关键。

动手验证
==========

用项目示例观察 func + arith 的协作：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir

确认输出中同时出现 ``func.func`` 、``arith.addi`` 、``func.return`` 三个 Dialect 的操作。
然后运行完整降级：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts

观察 ``func.func`` → ``llvm.func`` 、``arith.addi`` → ``llvm.add`` 的一一映射。

本章小结
========

func/arith/math 是 MLIR 降级管道的"主干骨架"：func 提供结构，arith 提供计算，
math 补充超越基本四则的数学函数。几乎所有端到端管道都会经过它们。

下一节 :ref:`mlir-03-03-03` 将介绍控制流 Dialect：scf 与 cf 。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
