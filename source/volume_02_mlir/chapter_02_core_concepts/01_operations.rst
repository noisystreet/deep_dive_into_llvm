.. _mlir-02-02-01:

=====================
Operation 与 Value
=====================

在 MLIR 中，**Operation** （操作）是构建一切的基本单元。一个 Operation 可以表示：
一条算术指令、一个函数定义、一个循环、乃至整个模块。**在 MLIR 中，一切皆 Operation**。

.. rst-class:: center

   LLVM IR 中 "Instruction" 和 "Function" 是不同的概念；在 MLIR 中，
   它们都统一为 **Operation**——唯一的区别是参数的构成方式不同。

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

1. **结果值** （``%sum`` ）：Operation 的 SSA 输出（可选，有的 Operation 没有输出）
2. **名称** （``arith.addi`` ）：由 Dialect 前缀（``arith`` ）和操作名（``addi`` ）组成
3. **操作数** （``%a, %b`` ）：输入 SSA 值
4. **属性字典** （可选）：编译期已知的元数据
5. **区域列表** （可选）：嵌套的子程序结构（函数体、循环体等）
6. **结果类型** （``: i32`` ）：输出值的类型

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
