.. _mlir-04-04-02:

=====================
定义 Operation
=====================

用 ODS 定义 Operation 是 MLIR 开发中最常见的任务。本节通过一个完整的例子，
逐步讲解如何定义 Operation 及其核心属性。

.. rst-class:: center

   定义一个 Operation = 告诉 MLIR 它的名字、参数、结果、汇编格式和约束。

一个完整的 Op 定义
=========================

.. code-block:: text

   // MulOp：整数乘法
   def MulOp : Op<MyDialect, "mul"> {
       // 1. 文档
       let summary = "Integer multiplication";
       let description = [{
           Performs integer multiplication on two values of the same type.
           The result type is the same as the operand type.
           Example:
           %result = my_dialect.mul %a, %b : i32
       }];

       // 2. 参数（arguments）和结果（results）
       let arguments = (ins I32:$lhs, I32:$rhs);
       let results = (outs I32:$result);

       // 3. 汇编格式
       let assemblyFormat = "$lhs `,` $rhs attr-dict";

       // 4. 验证器（可选）
       let verifier = [{
           if (getLhs().getType() != getRhs().getType())
               return emitOpError("operand type mismatch");
           return success();
       }];
   }

参数（Arguments）的类型
==============================

ODS 支持多种参数类型：

**值类型参数（Value-based）**

.. code-block:: text

   // 标量类型
   I32:$input                // 32 位整数
   F32:$input                // 32 位浮点
   Index:$input              // index 类型

   // 张量/向量类型
   TensorOf<[F32]>:$input    // f32 张量
   VectorOf<[I32]>:$input    // i32 向量
   AnyTensor:$input          // 任意张量

   // 类型约束
   SignlessIntegerLike:$x    // 无符号整数或向量/张量中的整数
   FloatLike:$x              // 浮点或向量/张量中的浮点

**属性参数（Attribute-based）**

.. code-block:: text

   // 编译期属性（不是 SSA 值）
   I32Attr:$stride           // 整数属性
   F32Attr:$value            // 浮点属性
   StrAttr:$name             // 字符串属性
   BoolAttr:$fastmath        // 布尔属性
   DenseI32ArrayAttr:$shape  // 整数数组属性

**变长参数和可选参数**

.. code-block:: text

   // 变长参数（零个或多个）
   Variadic<I32>:$inputs     // 可变数量的 i32

   // 可选参数（零个或一个）
   Optional<I32>:$maybe

名称约定：SSA 值使用 ``$`` 前缀，属性也使用 ``$`` 前缀。

结果（Results）的类型
============================

结果的定义语法和参数一致：

.. code-block:: text

   // 单个结果
   let results = (outs I32:$result);

   // 多个结果
   let results = (outs I32:$output1, F32:$output2);

   // 变长结果
   let results = (outs Variadic<I32>:$outputs);

   // 无结果（纯副作用操作）
   let results = (outs);

汇编格式（AssemblyFormat）
================================

ODS 可以通过声明式语法指定汇编格式，无需手写解析器。

**直接量（字面量）**

.. code-block:: text

   // 使用反引号括起来的字面量
   let assemblyFormat = "`my_op` $input attr-dict";
   // 输出：my_op %input

**操作数引用**

.. code-block:: text

   // 按名称引用操作数和结果
   let assemblyFormat = "$lhs `+` $rhs attr-dict";
   // 输出：%lhs + %rhs

**属性打印**

.. code-block:: text

   // 属性的打印格式
   let assemblyFormat = "$input `stride=` $stride attr-dict";

**指令式格式**

.. code-block:: text

   // 使用 `:` 分隔类型
   let assemblyFormat = "$lhs `,` $rhs attr-dict `:` type($result)";
   // 输出：%lhs, %rhs : i32

   // 使用 `(` 和 `)` 分组
   let assemblyFormat = "`(` $input `)` attr-dict";
   // 输出：(%input)

**自定义解析（手写）**

如果声明式格式不够用：

.. code-block:: text

   let hasCustomAssemblyFormat = 1;

然后在 C++ 中实现 ``parse`` 和 ``print`` 方法：

.. code-block:: cpp

   ParseResult MulOp::parse(OpAsmParser &parser, OperationState &result) {
       // 手写解析逻辑
   }
   void MulOp::print(OpAsmPrinter &p) {
       // 手写打印逻辑
   }

Op 的文档属性
=====================

.. code-block:: text

   def MyOp : Op<MyDialect, "my_op"> {
       let summary = "单行简介";              // 显示在文档中
       let description = [{                   // 详细描述
           Longer description here.
           Can span multiple lines.
       }];
   }

``summary`` 和 ``description`` 被 Sphinx 文档生成工具使用，也可以被
``mlir-query`` 工具查询。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
