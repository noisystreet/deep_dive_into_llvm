.. _mlir-05-05-03:

========================
Traits 与 Interfaces
========================

Operation 的行为由 **Traits** （特性）和 **Interfaces** （接口）控制。
它们定义了 Operation 的约束和功能，如是否可交换、是否满足 SSA 要求等。

.. rst-class:: center

   Traits 是"你是什么"（属性），Interfaces 是"你能做什么"（行为）。

.. admonition:: Trait vs Interface：编译期标签 vs 运行时多态
   :class: note

   这个区分借鉴了面向对象设计中"类注解"与"接口"的思想：

   - **Trait** 在编译期确定——``Pure`` 表示无副作用，优化器看到就能 DCE
   - **Interface** 在运行期查询——``LoopLikeOpInterface`` 让 Pass 对
     ``scf.for`` 和 ``affine.for`` 调用统一的 ``getLoopBounds()``

   LLVM 没有等价机制：判断一条指令是否可交换，得写 ``isa<BinaryOperator>``
   再加操作码检查。MLIR 的 Trait/Interface 让通用优化 Pass 的代码量
   减少一个数量级——``Canonicalizer`` 就是靠 Trait 批量识别可简化模式的。

Traits（特性）
==================

Traits 是编译期的属性，在 Operation 定义时附加。它们影响 MLIR 框架如何
处理 Operation。

**内置 Trait**

.. code-block:: text

   def AddOp : Op<MyDialect, "add", [
       Commutative,           // 可交换（a+b = b+a）
       SameTypeOperands       // 所有操作数类型相同
   ]> {
       let arguments = (ins I32:$lhs, I32:$rhs);
       let results = (outs I32:$result);
   }

常见的 MLIR 内置 Traits：

.. list-table:: 常用内置 Trait
   :header-rows: 1

   * - Trait
     - 含义
     - 效果
   * - ``Commutative``
     - 操作可交换
     - 优化器可以交换操作数
   * - ``SameTypeOperands``
     - 所有操作数类型相同
     - 自动添加类型验证
   * - ``SameOperandsAndResultType``
     - 操作数和结果类型相同
     - 自动添加类型验证
   * - ``ConstantLike``
     - 操作没有副作用
     - 允许 CSE（公共子表达式消除）
   * - ``NoSideEffect``
     - 操作无副作用
     - 可以删除未使用的操作
   * - ``IsTerminator``
     - 终止操作（控制流终点）
     - Block 必须以它结尾
   * - ``SingleBlock``
     - 只有一个 Block
     - Region 中有且仅有一个 Block
   * - ``NoRegionArguments``
     - Region 没有参数
     - Block 无参数

**自定义 Trait**

可以定义自己的 Trait：

.. code-block:: cpp

   // C++ 中定义 Trait
   template <typename ConcreteType>
   class MyTrait : public TraitBase<ConcreteType, MyTrait> {
   public:
       // 可以重写以下方法
       static LogicalResult verifyTrait(Operation *op) {
           // 验证逻辑
           return success();
       }
   };

在 ODS 中使用自定义 Trait：

.. code-block:: text

   def MyOp : Op<MyDialect, "my_op", [
       MyTrait
   ]> { ... }

Interfaces（接口）
======================

Interfaces 定义了 Operation 必须实现的**方法签名**。MLIR 使用 ``OpInterface``
来声明这些接口。

**内置 Interface 示例**

.. code-block:: text

   def MyOp : Op<MyDialect, "my_op", [
       LoopLikeOpInterface  // 要求实现 LoopLike 接口
   ]> { ... }

**常见的 MLIR 接口**：

.. list-table:: 常用 Interface
   :header-rows: 1

   * - Interface
     - 要求实现的方法
     - 用途
   * - ``LoopLikeOpInterface``
     - ``getLoopInductionVars()`` 等
     - 循环相关的优化 Pass 使用
   * - ``CallOpInterface``
     - ``getCallableForCallee()``
     - 函数调用的统一处理
   * - ``RegionBranchOpInterface``
     - ``getSuccessorRegions()``
     - Region 间的控制流分析
   * - ``InferTypeOpInterface``
     - ``inferReturnTypes()``
     - 自动推断结果类型
   * - ``MemoryEffectOpInterface``
     - ``getEffects()``
     - 内存效应分析

**InferTypeOpInterface：类型推断**

最常见的 Interface 之一是 ``InferTypeOpInterface``：
它让 Operation 可以自动推断结果类型，不用显式指定。

.. code-block:: text

   def AddOp : Op<MyDialect, "add", [
       InferTypeOpInterface  // 自动推断结果类型
   ]> {
       let arguments = (ins I32:$lhs, I32:$rhs);
       let results = (outs I32:$result);// 类型由 infer 函数推断

       let builders = [
           OpBuilder<(ins "Value":$lhs, "Value":$rhs)>
       ];

       let hasFolder = 1;
   }

对应的 C++ 实现：

.. code-block:: cpp

   LogicalResult AddOp::inferReturnTypes(
       MLIRContext *context, Optional<Location> location,
       ValueRange operands, DictionaryAttr attrs,
       OpaqueProperties properties, RegionRange regions,
       SmallVectorImpl<Type> &inferredReturnTypes) {
       // 结果类型与操作数类型相同
       inferredReturnTypes.push_back(operands[0].getType());
       return success();
   }

Traits vs Interfaces 的选择
==================================

.. list-table:: Traits vs Interfaces
   :header-rows: 1

   * - 特征
     - Traits
     - Interfaces
   * - 定义方式
     - C++ 模板类或 ODS
     - ODS（OpInterface）
   * - 编译期/运行时
     - 编译期
     - 运行时
   * - 可以携带数据
     - 是
     - 否（只有方法签名）
   * - 验证功能
     - ``verifyTrait()``
     - 无（在实现中验证）
   * - 多态性
     - 静态多态
     - 动态多态
   * - 典型用途
     - 标记属性（可交换、无副作用）
     - 行为抽象（循环、函数调用）

简单规则：**若只需标记属性，用 Trait；若需定义方法签名，用 Interface**。

访问 Traits 和 Interfaces 的 C++ 接口
===========================================

.. code-block:: cpp

   // 检查 Operation 是否有某个 Trait
   if (op->hasTrait<Commutative>()) {
       // 可以交换操作数
   }

   // 调用 Interface 方法
   if (auto loopOp = dyn_cast<LoopLikeOpInterface>(op)) {
       auto ivs = loopOp.getLoopInductionVars();
   }

源码走读：Trait 与 Interface 的生成
======================================

Trait 的 ODS 定义在
`OpBase.td <file:///workspace/llvm-project/mlir/include/mlir/IR/OpBase.td>`__ 中，
Interface 通过 ``OpInterface`` 类在 ``.td`` 文件中声明方法签名，
由 ``mlir-tblgen`` 生成 C++ 虚接口。

以 ``NoMemoryEffect`` Trait 为例，它告诉优化器该 Operation 没有副作用，
可以被自由 CSE 和 DCE——:ref:`mlir-03-03-02` 中 ``Arith_Op`` 基类
就附加了这个 Trait。

``LoopLikeOpInterface`` 则抽象了所有"类循环"操作的公共方法
（``getLoopInductionVars()``、``getLoopBounds()`` 等），
定义见
`LoopLikeInterface.td <file:///workspace/llvm-project/mlir/include/mlir/Interfaces/LoopLikeInterface.td>`__ ，
使得循环优化 Pass 可以统一处理 ``scf.for``、``affine.for`` 等不同 Op。

动手验证
==========

检查 arith Dialect 中 Trait 的使用：

.. code-block:: console

   rg "NoMemoryEffect|Commutative" \
       llvm-project/mlir/include/mlir/Dialect/Arith/IR/ArithOps.td | head -5

本章小结
========

Trait 标记编译期属性，Interface 定义运行时行为契约——两者让 MLIR 的 Operation
既有多态性，又保持高效。ODS 自动生成这些机制的 C++ 代码，是 MLIR 可扩展性的关键。

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
