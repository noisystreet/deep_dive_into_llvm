.. _mlir-02-02-01:

=====================
Operation 与 Value
=====================

在 MLIR 中，**Operation** （操作）是构建一切的基本单元。一个 Operation 可以表示：
一条算术指令、一个函数定义、一个循环、乃至整个模块。**在 MLIR 中，一切皆 Operation**。

.. rst-class:: center

   LLVM IR 中 "Instruction" 和 "Function" 是不同的概念；在 MLIR 中，
   它们都统一为 **Operation**——唯一的区别是参数的构成方式不同。

.. admonition:: "一切皆 Operation"——从 Lisp S 表达式到 MLIR
   :class: note

   MLIR 的 "一切皆 Operation" 设计哲学，在编译器的历史上并不新鲜。
   早在 1958 年，John McCarthy 设计的 **Lisp** 就提出了"一切皆列表"
   （code is data）的概念——程序和数据用同一种结构表示。

   MLIR 把它复用到了编译器领域：**一个函数是一个 Operation、一条指令
   是一个 Operation、一个循环是一个 Operation、甚至整个模块也是一个
   Operation**。这种设计的最大好处是：你只需要**一套统一的工具**就能
   操作所有东西——遍历、匹配、替换、验证。

   这和 LLVM IR 形成鲜明对比：LLVM 中 Instruction、BasicBlock、Function、
   Module 是**不同的 C++ 类**，各有各的 API。遍历 IR 需要根据不同层级
   使用不同的方法（ ``inst_iterator``、``BasicBlock::iterator``、``Function::iterator`` ）。
   而在 MLIR 中，无论什么层级，你都用同一个 ``Operation::getOperands()``、
   ``Operation::getRegions()``、``OpBuilder`` 来操作。

   这意味着你可以写出**通用的 IR 变换**——如"把 IR 中所有三地址码格式的
   Operation 替换为 SSA 格式"——而不需要关心这个 Operation 来自哪个
   Dialect。在 LLVM 中，这种"通用变换"几乎不可能写成通用的 Pass。

   当然，这种设计也有代价：MLIR 的类型系统比 LLVM 更复杂，而且
   "一切皆 Operation" 意味着即使是最简单的操作（如从某处加载一个值）
   也有比 LLVM 更深的类层次结构。这是**通用性 vs 性能**之间的经典权衡。

Operation 的结构
====================

一个 Operation 由以下几个部分构成：

.. code-block:: text

   %result = dialect.op_name(%arg0, %arg1)
       [属性字典]
       (区域列表)
       : 结果类型

   // 实际例子
   %sum = arith.addi %a, %b : i32

各部分含义：

1. **结果值** （ ``%sum`` ）：Operation 的 SSA 输出（可选，有的 Operation 没有输出）
2. **名称** （ ``arith.addi`` ）：由 Dialect 前缀（ ``arith`` ）和操作名（ ``addi`` ）组成
3. **操作数** （ ``%a, %b`` ）：输入 SSA 值
4. **属性字典** （可选）：编译期已知的元数据
5. **区域列表** （可选）：嵌套的子程序结构（函数体、循环体等）
6. **结果类型** （ ``: i32`` ）：输出值的类型

一个更复杂的例子：

.. code-block:: text

   // 带属性和区域的 Operation
   #map = affine_map<(d0, d1) -> (d0, d1)>
   func.func @main(%A: memref<4x4xf32>) {
       %sum = scf.for %i = %c0 to %c4 step %c1
           iter_args(%acc = %c0) -> i32 {
           %v = memref.load %A[%i] : memref<4x4xf32>
           %new = arith.addi %acc, %v : i32
           scf.yield %new : i32
       }
       return
   }

这里 ``func.func``、``scf.for``、``memref.load``、``arith.addi``、``scf.yield``
都是 Operation。

SSA Value
===============

MLIR 中的 **Value** 是 SSA 值（静态单赋值），每个 Value 恰好被一个 Operation
定义，可以被多个 Operation 使用。

.. code-block:: text

   %a = arith.constant 1 : i32          // 定义 %a
   %b = arith.constant 2 : i32          // 定义 %b
   %c = arith.addi %a, %b : i32        // 使用 %a, %b，定义 %c

   // %a 只能被定义一次，但可以被多次使用
   %d = arith.addi %c, %a : i32         // %a 被第二次使用

Value 有两个主要属性：

- **Type**：值的类型（如 ``i32``、``f32``、``tensor<4xf32>`` ）
- **definingOp**：定义这个值的 Operation（可以通过 ``value.getDefiningOp()`` 获取）

Block Arguments
======================

除了 Operation 定义的 Value，MLIR 中还有一种特殊的 Value：**Block 参数**。
Block 可以有参数，它们由控制流隐式定义，而不是由某个 Operation 显式定义：

.. code-block:: text

   // scf.for 的 Block 参数：
   // %i 是循环索引（由 scf.for 隐式提供）
   // %acc 是累加器（由 iter_args 指定初值，每次迭代被 scf.yield 更新）
   %sum = scf.for %i = %c0 to %c4 step %c1
       iter_args(%acc = %c0) -> i32 {
       %v = arith.addi %acc, %i : i32
       scf.yield %v : i32
   }

在这里，``%i`` 和 ``%acc`` 都是 Block 参数——它们不是由某个 ``arith.addi``
定义的，而是由控制流的进入点提供的。

Operation 的名称格式
===========================

每个 Operation 都有一个全局唯一的名称，格式为：``dialect.operation``。

.. list-table:: 常见 Operation 命名示例
   :header-rows: 1

   * - Dialect
     - Operation 示例
     - 语义
   * - ``arith``
     - ``arith.addi``
     - 整数加法
   * - ``scf``
     - ``scf.for``
     - 结构化 for 循环
   * - ``func``
     - ``func.func``
     - 函数定义
   * - ``memref``
     - ``memref.load``
     - 从内存加载
   * - ``linalg``
     - ``linalg.matmul``
     - 矩阵乘法
   * - ``tensor``
     - ``tensor.cast``
     - 张量类型转换

这种命名约定使得 Operation 的归属一目了然——看到 ``arith.addi`` 就知道
它属于 ``arith`` Dialect，具有算术语义。

定义 Operation 的方式
===========================

在 MLIR 中，有两种方式定义新的 Operation：

**1. 通过 C++ 直接定义（手动方式）**

.. code-block:: cpp

   class MyCustomOp : public Op<MyCustomOp> {
   public:
       using Op::Op;
       static StringRef getOperationName() { return "my_dialect.custom_op"; }
       // ... 实现接口方法
   };

**2. 通过 ODS（Operation Definition Spec，推荐方式）**

.. code-block:: text

   def MyCustomOp : Op<"my_dialect.custom_op"> {
       let summary = "My custom operation";
       let arguments = (ins I32:$input);
       let results = (outs I32:$output);
       let assemblyFormat = "$input attr-dict";
   }

ODS 方式基于 TableGen，可以自动生成解析、打印、验证等代码。我们将在第 4 章中
深入 ODS。

Operation 的验证
=====================

每个 Operation 都可以定义自己的**验证器** （verifier），在构造和转换时自动执行：

.. code-block:: cpp

   LogicalResult MyCustomOp::verify() {
       if (auto *parent = getParentOp()) {
           // 检查父操作是否满足某些条件
       }
       // 检查操作数的类型约束
       if (getInput().getType() != getOutput().getType()) {
           return emitOpError("input and output types must match");
       }
       return success();
   }

验证器保证了 IR 的正确性——不合法的 Operation 无法被构建或写入文件。

源码走读：Operation 类的内存布局
======================================

``Operation`` 是 MLIR 最核心的类，定义在
`Operation.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Operation.h>`__ 。

源码注释揭示了一个精巧的内存布局设计：

.. code-block:: text

   // 对于 3 个结果的 Operation，内存布局为：
   // [Result2, Result1, Result0, Operation]
   //                          ^ this is where Operation* points to

结果值紧邻 Operation 对象之前存储，使得遍历和操作都非常高效。
操作名中的 ``.`` 分隔 Dialect 前缀和操作名——这不是语法糖，
而是 MLIR 框架识别 Dialect 归属的正式机制。

对比第一卷 :ref:`chapter-02-03-module-function-basicblock` 中
LLVM IR 的 Instruction/Function 分层设计，MLIR 用统一的 Operation
类消除了层级差异，代价是单对象内存开销略大。

动手验证
==========

观察 Operation 在 IR 文本中的结构：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir

输出中每一行都是一个 Operation：``func.func`` 是 Operation，
``arith.addi`` 是 Operation，``func.return`` 也是 Operation——
唯一的区别是有无 Region 和属性。

本章小结
========

Operation 是 MLIR 的万能积木，Value 是 SSA 数据流的基本单元。
理解 Operation 的结构后，下一节 :ref:`mlir-02-02-02` 的类型与属性
系统就有了附着的基础。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
