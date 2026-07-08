.. _mlir-02-02-02:

=======================
类型系统与属性
=======================

MLIR 拥有一个**可扩展的类型系统**——这与 LLVM IR 的固定类型系统形成鲜明对比。
用户可以为自己的 Dialect 定义任意类型。

.. rst-class:: center

   LLVM IR 有固定的 ``i32``、``ptr``、``float`` 等类型；MLIR 允许你定义
   ``tensor<4x4xf32>``、``memref<1024xf64>`` 或任何你需要的类型。

Type（类型）
================

MLIR 中的 Type 是一个抽象基类。所有的具体类型都继承自它：

.. code-block:: text

   Type
   ├── IntegerType       (i32, i64, i1)
   ├── FloatType         (f32, f64, bf16)
   ├── VectorType        (vector<4xf32>)
   ├── TensorType        (tensor<4x4xf32>)
   │   ├── RankedTensorType
   │   └── UnrankedTensorType
   ├── MemRefType        (memref<1024xf32>)
   ├── LLVMStructType   (来自 LLVM Dialect)
   └── 自定义 Type       (用户定义)

一个 MLIR 类型的示例：

.. code-block:: text

   // 基础类型
   i32                         // 32 位整数
   f64                         // 64 位 IEEE 浮点数
   i1                          // 布尔（1 位整数）

   // 复合类型
   tensor<4x4xf32>             // 4x4 张量，元素类型 f32
   memref<1024xf64, 2>         // 1024 元素缓冲区，地址空间 2
   vector<16xi32>              // 16 个 i32 的向量
   !llvm.struct<(i32, f64)>    // LLVM 结构体类型

Type 的约束
================

类型可以带约束。例如 ``TensorType`` 的类型参数可以是特定元素类型或泛型：

.. code-block:: text

   tensor<4x4xf32>              // 具体类型
   tensor<*xf32>                // 任意形状的 f32 张量
   tensor<4x4x?xf32>            // 最后一维动态的 4x4 张量
   tensor<*x?xf32>              // 形状和部分维度都未知

在 Operation 的定义中，可以通过 ODS 约束操作数的类型关系：

.. code-block:: text

   // 定义加法操作：两个输入类型必须一致，输出与输入类型一致
   def AddOp : Op<"arith.addi"> {
       let arguments = (ins SignlessIntegerLike:$lhs, SignlessIntegerLike:$rhs);
       let results = (outs SignlessIntegerLike:$result);
       let assemblyFormat = "$lhs `,` $rhs attr-dict";
   }

Attribute（属性）
======================

Attribute 是编译期确定的**元数据**，附着在 Operation 上。与 Value 不同，
Attribute 在运行时不可变，并且不参与 SSA 数据流。

.. code-block:: text

   // 属性示例
   %c = arith.constant dense<[1, 2, 3]> : tensor<3xi32>
   //              ^^^^^ 这是 DenseElementsAttr 属性

常见的 Attribute 类型：

.. list-table:: MLIR 内置 Attribute 类型
   :header-rows: 1

   * - Attribute 类型
     - 语法示例
     - 说明
   * - ``IntegerAttr``
     - ``42``
     - 整数常量
   * - ``FloatAttr``
     - ``3.14``
     - 浮点常量
   * - ``StringAttr``
     - ``"hello"``
     - 字符串
   * - ``DenseElementsAttr``
     - ``dense<[1, 2, 3]>``
     - 密集型张量数据
   * - ``SparseElementsAttr``
     - ``sparse<[[0,0], 1]>``
     - 稀疏型张量数据
   * - ``ArrayAttr``
     - ``[1, 2, 3]``
     - 属性数组
   * - ``DictionaryAttr``
     - ``{name = "foo", size = 32 : i64}``
     - 属性字典
   * - ``TypeAttr``
     - ``type<i32>``
     - 类型属性（指向一个 Type）
   * - ``UnitAttr``
     - ``unit``
     - 布尔标记（存在 vs 不存在）

Attribute vs Value
======================

对于新手来说，最常见的混淆点就是 Attribute 和 Value 的区别。

.. list-table:: Attribute vs Value
   :header-rows: 1

   * - 特征
     - Attribute
     - Value
   * - 定义时机
     - 编译期
     - 运行时
   * - 是否参与 SSA
     - 否
     - 是
   * - 可变性
     - 不可变
     - 不可变（SSA）
   * - 存储位置
     - 直接附在 Operation 上
     - 由 Operation 定义
   * - 典型用途
     - 常量、步长、形状参数
     - 变量、计算中间结果

Attribute 的典型用法：

.. code-block:: text

   // stride 和 dilations 是属性（编译期确定）
   %0 = linalg.conv_2d
       ins(%input, %filter : tensor<224x224x3xf32>, tensor<3x3x3x64xf32>)
       outs(%output : tensor<224x224x64xf32>)
       { strides = [2, 2], dilations = [1, 1] }

内置 vs 自定义 Type
============================

MLIR 框架内置了一些常用类型（如 ``IntegerType``、``FloatType`` ），但 Dialect
可以注册自己的类型：

.. code-block:: text

   // 内置类型
   i32, f64, tensor<4x4xf32>

   // 自定义类型（来自 LLVM Dialect）
   !llvm.ptr<i32>       // i32 指针
   !llvm.struct<(i32, f64)>  // 结构体

   // 自定义类型（来自用户 Dialect）
   !my_dialect.complex<f64>  // 复数类型

自定义类型的注册方式和 Operation 类似——通过 ODS 定义，由 ``mlir-tblgen``
生成代码。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
