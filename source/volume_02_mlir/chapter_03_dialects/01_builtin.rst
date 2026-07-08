.. _mlir-03-03-01:

=================
builtin Dialect
=================

``builtin`` Dialect 是 MLIR 中最基础的 Dialect。它定义了一组**所有 MLIR 程序**
都需要的核心类型和操作，不需要显式导入。

.. rst-class:: center

   你可以把 ``builtin`` 理解为 MLIR 的"标准库"——它提供了语言的基础设施，
   任何 Dialect 都可能用到它定义的类型和操作。

ModuleOp：顶层容器
========================

每个 MLIR 程序的最顶层都是一个 ``ModuleOp``。它是整个 IR 的根容器。

.. code-block:: text

   // 一个完整的 MLIR 模块
   module {
       func.func @main() -> i32 {
           %c = arith.constant 42 : i32
           return %c : i32
       }
   }

``ModuleOp`` 的功能：

- 容纳所有顶级 Operation（函数、全局变量、类型定义等）
- 提供符号（symbol）的作用域——函数名、全局变量名等在 Module 内唯一
- 在降级过程中，``ModuleOp`` 最终会映射为 LLVM IR 中的 ``llvm::Module``

ModuleOp 验证规则：

.. code-block:: text

   // 非法：两个同名函数
   module {
       func.func @main() -> i32 { ... }
       func.func @main() -> f32 { ... }  // 错误：重复符号
   }

UnrealizedConversionCastOp
==============================

在 Dialect Conversion 过程中，当两个阶段的类型不完全匹配时，MLIR 会插入
**UnrealizedConversionCastOp** 作为桥梁。这个 Operation 在最终的降级完成前
必须被消除：

.. code-block:: text

   // 类型转换时的中间状态
   // tensor<4xf32> → memref<4xf32> 需要插入 cast
   %0 = tensor.cast %input : tensor<4xf32> to tensor<4xf32>
   %1 = unrealized_conversion_cast %0 : tensor<4xf32> to memref<4xf32>
   //       ^^^^^^^^^^^^^^^^^^^^^^^^ 这个 cast 必须在最终代码生成前消除

如果 finalization 之后还有未被消除的 ``UnrealizedConversionCastOp``，
说明降级不完整，MLIR 会报错。

内置类型
================

``builtin`` Dialect 定义了 MLIR 中最常用的类型。以下是其中最重要的几类：

.. list-table:: builtin 核心类型
   :header-rows: 1

   * - 类型
     - 示例
     - 说明
   * - ``IntegerType``
     - ``i1``、``i8``、``i32``、``i64``
     - 任意位宽的整数
   * - ``FloatType``
     - ``f16``、``f32``、``f64``、``bf16``
     - IEEE 浮点数
   * - ``NoneType``
     - ``none``
     - 无类型（类似 void）
   * - ``FunctionType``
     - ``(i32, i32) -> i32``
     - 函数签名
   * - ``IndexType``
     - ``index``
     - 平台相关的整数（用于循环索引、数组下标）

这些类型之所以属于 ``builtin`` 而不是特定的 Dialect，是因为它们非常基础——
几乎所有 Dialect 都需要引用这些类型来构建自己的类型和操作。

FunctionType
================

``FunctionType`` 是所有函数调用的类型基础：

.. code-block:: text

   // 函数类型：接受两个 i32，返回 i32
   !func_type = (i32, i32) -> i32

   // 无参数无返回值
   !void_func = () -> ()

在 MLIR 中，函数类型被显式地写出来——这与 LLVM IR 不同（LLVM IR 中
函数类型隐含在函数定义中）：

.. code-block:: text

   // func.func 的签名字面上隐含着 FunctionType
   func.func @add(%a: i32, %b: i32) -> i32 {
       %r = arith.addi %a, %b : i32
       return %r : i32
   }

内置 Attribute
=====================

``builtin`` 也定义了一组基础 Attribute，前文第 2 章已经详细介绍过。
这里补充一个常用场景——在 Operation 中使用 ``ArrayAttr`` 和 ``DictionaryAttr``：

.. code-block:: text

   // ArrayAttr：一组属性的有序数组
   %0 = "my_dialect.op"() {values = [1, 2, 3]} : () -> i32

   // DictionaryAttr：键值对
   %0 = "my_dialect.op"() {config = {mode = "fast", debug = false}} : () -> i32

符号表（Symbol Table）
===========================

``builtin`` Dialect 定义了 **Symbol Table** 接口。任何实现该接口的 Operation
都可以作为符号表使用（最典型的就是 ``ModuleOp`` ）：

.. code-block:: cpp

   // 通过符号表查找符号
   auto *moduleOp = getOperation();
   auto symTable = moduleOp->getAttrOfType<SymbolTable>(
       SymbolTable::getSymbolAttrName());
   auto *funcOp = symTable.lookup("main");

符号表在跨 Operation 引用中非常关键，比如函数调用需要通过符号表查找被调用者。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
