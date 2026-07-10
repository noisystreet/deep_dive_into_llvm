.. _mlir-05-05-04:

===========================
用 ODS 定义类型和属性
===========================

ODS 不仅能定义 Operation，还能定义 **Type** 和 **Attribute** 。这让你可以在
ODS 中完整地描绘 Dialect 的数据类型系统。

.. rst-class:: center

   Operation 定义了"做什么"，Type 定义了"对什么做"。

.. admonition:: StorageUniquer：指针比较即相等
   :class: note

   MLIR 中 ``IntegerType::get(ctx, 32)`` 无论调用多少次，返回的都是
   **同一个对象** 。这靠 ``StorageUniquer`` 实现：每种 Type/Attribute
   按参数唯一化存储，判等只需比较指针。

   这与 LLVM ``Type`` 的唯一化策略一脉相承，但 MLIR 扩展到了
   用户自定义 Type——``!llvm.struct<"desc", i32, i64>`` 也是唯一化的。
   性能意义：Verifier 和 Pattern Rewrite 中大量类型比较变成 O(1) 指针比较，
   而非字符串或结构体逐字段比较。

用 ODS 定义 Type
======================

**TypeDef** 是 ODS 中定义 Type 的关键字：

.. code-block:: text

   // 定义一个复数类型
   def ComplexType : TypeDef<MyDialect, "Complex"> {
       let mnemonic = "complex";
       let summary = "A complex number type";

       let parameters = (ins "Type":$elementType);

       let assemblyFormat = "`complex<` $elementType `>`";
   }

使用这个类型：

.. code-block:: text

   // 在 IR 中使用
   %c = my_dialect.op : !my_dialect.complex<f64>

   // 在 C++ 中
   ComplexType cType = ComplexType::get(f64Type);
   cType.getElementType();  // 返回 f64Type

**带简单参数的 Type**

.. code-block:: text

   // 定长向量类型
   def FixedVectorType : TypeDef<MyDialect, "FixedVector"> {
       let mnemonic = "fixed_vec";
       let parameters = (ins "unsigned":$size, "Type":$elementType);
       let assemblyFormat = "`fixed_vec<` $size `x` $elementType `>`";
   }

   // IR：!my_dialect.fixed_vec<4xf32>

**TypeDef 的 verify 方法**

.. code-block:: text

   def PositiveIntType : TypeDef<MyDialect, "PositiveInt"> {
       let mnemonic = "pos_int";
       let parameters = (ins "int64_t":$value);
       let assemblyFormat = "`pos_int<` $value `>`";

       let verifier = [{
           if (getValue() <= 0)
               return emitError("value must be positive");
           return success();
       }];
   }

用 ODS 定义 Attribute
============================

**AttrDef** 用于定义自定义的 Attribute：

.. code-block:: text

   // 定义一个颜色属性
   def ColorAttr : AttrDef<MyDialect, "Color"> {
       let mnemonic = "color";
       let summary = "A color attribute (RGB)";

       let parameters = (ins
           "uint8_t":$red,
           "uint8_t":$green,
           "uint8_t":$blue
       );

       let assemblyFormat = "`color<` $red `,` $green `,` $blue `>`";
   }

在 Operation 中使用：

.. code-block:: text

   def SetColorOp : Op<MyDialect, "set_color"> {
       let arguments = (ins
           MyDialect_ColorAttr:$color  // 使用自定义属性
       );
       let assemblyFormat = "$color attr-dict";
   }

   // IR：my_dialect.set_color color<255, 0, 0>

**带默认值的 Attribute**

.. code-block:: text

   def PrecisionAttr : AttrDef<MyDialect, "Precision"> {
       let mnemonic = "precision";
       let parameters = (ins "int64_t":$bits);
       let assemblyFormat = "`prec<` $bits `>`";

       // 默认值
       let defaultValue = "PrecisionAttr::get(context, 32)";
   }

生成的文件
===============

ODS 定义 Type 和 Attribute 后，``mlir-tblgen`` 会生成：

.. code-block:: text

   MyDialectTypes.h.inc：
   - class ComplexType
   - class FixedVectorType
   - class ColorAttr
   - 每个类有 get()、getChecked() 等静态方法
   - 每个类有参数访问器（getElementType() 等）
   - 序列化/反序列化代码

在 Dialect 中注册

.. code-block:: cpp

   // 在 Dialect 初始化时注册类型和属性
   void MyDialect::initialize() {
       addTypes<ComplexType, FixedVectorType>();
       addAttributes<ColorAttr, PrecisionAttr>();
   }

参数化 Type 的存储机制
=============================

MLIR 的 Type 和 Attribute 采用 **uniquing** （唯一化）存储——相同的 Type
或 Attribute 只存储一次（类似 LLVM 中的 ``StringPool`` ）：

.. code-block:: cpp

   // 这里返回的是同一个 Type 实例（指针相等）
   auto t1 = ComplexType::get(ctx, f64Ty);
   auto t2 = ComplexType::get(ctx, f64Ty);
   assert(t1 == t2);  // 指针相等

这是因为 MLIR 的 StorageUniquer 机制保证了同类型实例的唯一性。

源码走读：TypeDef 与 AttrDef
======================================

自定义 Type 和 Attribute 通过 ODS 的 ``TypeDef`` 和 ``AttrDef`` 类定义，
生成逻辑与 ``Op`` 类似。内置类型的唯一化实现在
`StorageUniquer.h <file:///workspace/llvm-project/mlir/include/mlir/Support/StorageUniquer.h>`__ 。

LLVM Dialect 的 ``!llvm.struct<...>`` 类型就是参数化 Type 的典型应用——
memref 降级时生成的描述符结构体，详见 :ref:`mlir-11-06-03` 。

动手验证
==========

观察 LLVM Dialect 中的复合类型：

.. code-block:: console

   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts

输出中的 ``i32`` 是内置 Type，由 ``BuiltinTypes.h`` 定义。

本章小结
========

ODS 不仅定义 Operation，也定义 Type 和 Attribute。
三者在 ``mlir-tblgen`` 的生成体系中地位平等，共同构成一个 Dialect 的完整描述。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
