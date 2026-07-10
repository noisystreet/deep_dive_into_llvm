.. _mlir-01-01-02:

===================
MLIR 的设计哲学
===================

上一节我们看到了 MLIR 的动机：传统编译器需要一个可扩展的多层 IR 框架。
本节深入 MLIR 的核心设计哲学——这些哲学贯穿了整个 MLIR 的设计和实现。

.. rst-class:: center

   MLIR 最核心的设计原则是： **渐进降级** （Progressive Lowering）和
   **第一类 Dialect 机制** （First-class Dialects）。

.. admonition:: "方言"一词的由来：编译器里的巴别塔
   :class: note

   MLIR 把可插拔的 IR 扩展称为 **Dialect** （方言）——这个命名很形象：
   就像不同地区说不同方言，不同领域也需要不同的 IR "方言"。
   TensorFlow 说 TOSA，PyTorch 说 Torch，硬件设计说 HW，但它们共享
   同一套 **Operation / Type / Pass** 基础设施。

   这与 LLVM 形成对比：LLVM 只有一套 IR，新领域只能往里面"硬塞" intrinsics
   或 metadata。MLIR 允许你 **先定义自己的 Dialect，再逐步降级到公共层**——
   CIRCT（芯片设计）、IREE（推理引擎）、Buddy（向量扩展）都是这条路的成功案例。

Progressive Lowering（渐进降级）
======================================

**渐进降级** 是 MLIR 最重要的设计哲学。它指的是： **不要求从源语言一步降到
机器码，而是通过多层 IR，逐步降低抽象级别，每一层都在合适的粒度上进行优化** 。

对比两条路径：

.. code-block:: text

   传统方式（一步到底）：
     Python 源码 → LLVM IR → 机器码
                     ↑
             在 LLVM IR 上做所有优化

   MLIR 方式（渐进降级）：
     Python 源码 → HLO（高级操作）→ linalg（线性代数）→ scf（控制流）
                 → arith（算术）→ LLVM Dialect → LLVM IR → 机器码
                    ↑            ↑            ↑
                高级优化      中层优化     底层优化

每一层的典型优化：

.. list-table:: 各抽象层次的典型优化
   :header-rows: 1

   * - 层次
     - 典型 Dialect
     - 典型优化
   * - 最上层（领域特定）
     - TOSA、StableHLO
     - 算子融合、算子替换、常量折叠
   * - 中层（结构化）
     - linalg、scf、tensor
     - 循环分块（Tiling）、循环融合、内存规划
   * - 底层（标量）
     - arith、memref、LLVM
     - 常数传播、死代码消除、指令选择

最高层的 Dialect 直接对应源语言的语义——比如 TOSA 中一个 ``matmul`` 操作
对应一次矩阵乘法。优化器不需要猜测"这堆 add/mul 是不是矩阵乘法"。

First-class Dialect（第一类方言）
=========================================

MLIR 中的 **Dialect** （方言）是 MLIR 框架中最核心的扩展机制。一个 Dialect
定义了一组 Operation、Type、Attribute，以及它们的语义。

Dialect 是"第一类"（first-class）的——这意味着：

1. **MLIR 框架对任何 Dialect 一视同仁** ：没有"内建"和"第三方"的区别
2. **用户自定义的 Dialect 和 MLIR 内置的 Dialect 享有完全相同的地位**
3. **Dialect 之间的转换通过显式的 Lowering Pass 完成**

.. code-block:: text

   // Dialect 在 MLIR 中的表示：
   // 每个操作都以 dialect_name.op_name 的形式命名
   %0 = arith.addi %a, %b : i32        // arith Dialect 的加法
   %1 = scf.for %i = %0 to %n step %s  // scf Dialect 的循环
   %2 = linalg.matmul %A, %B            // linalg Dialect 的矩阵乘法

   格式：dialect.operation 参数列表 : 结果类型

区分不同 Dialect 的操作是有意义的——因为优化器可以根据操作所属的 Dialect
来判断它蕴含的语义。

SSA 作为基础，但不强制
==================================

LLVM IR 要求严格遵循 SSA 形式——每个值恰好定义一次。MLIR 不同：
**MLIR 的 Operation 之间基于 SSA 的 Value 传递数据，但 Operation 内部
的 Region 可以使用自己的控制流约定** 。

.. code-block:: text

   // MLIR 中可以使用 SSA 值
   %c = arith.addi %a, %b : i32

   // scf.for 使用 Region（而非 phi 节点）表示循环
   %sum = scf.for %i = %c0 to %n step %c1
       iter_args(%acc = %c0) -> i32 {
       %v = arith.addi %acc, %i : i32
       scf.yield %v : i32
   }

这个设计既保留了 SSA 的优点（明确的 def-use 链），又允许更自然地表达
控制流结构（Region 中的 Block 可以有自己的参数）。

Block Arguments 优于 PHI 节点
============================================

MLIR 选择用 **Block Arguments**\ （块参数）而非 LLVM 的 **PHI 节点**\ 来
表示 SSA 中的控制流汇合。`Rationale.md <file:///workspace/llvm-project/mlir/docs/Rationale/Rationale.md>`__
中列出了 5 个具体优势：

**1. 消除"必须在顶部"的人为限制**

LLVM 的 PHI 节点必须始终位于 BasicBlock 的顶部，所有变换都需要手动
跳过它们。Block Arguments 是 Block 定义的 **固有属性** ，不存在"位置"
问题，变换代码更简洁。

.. code-block:: text

   // LLVM IR：PHI 必须在 block 顶部
   loop:
     %val = phi i32 [ 0, %entry ], [ %next, %body ]  ; 必须在顶部
     %tmp = add i32 %val, 1                           ; 在 PHI 之后
     ...

   // MLIR：Block Arguments 是 block 定义的一部分
   ^loop(%val: i32):               ; 参数在 block 入口处
     %tmp = arith.addi %val, %c1 : i32
     ...

**2. 统一函数参数和 Block 参数**

LLVM 中函数参数（ ``Function::arg_begin()`` ）和 PHI 节点是两套不同的
机制。MLIR 用 Block Arguments 统一了二者——**入口 Block 的参数就是函数参数** 。

**3. 消除 PHI 的原子执行语义**

LLVM 中同一 Block 的所有 PHI 节点 **同时执行** （atomic semantics），
这看似简单，但实际上经常导致"lost copy"问题——当需要将 PHI 节点
转换为普通指令时，值的交换顺序很容易出错。Block Arguments 不存在
这种问题，因为参数在进入 Block 时就已经确定。

**4. 消除无序 PHI 列表的性能陷阱**

LLVM 的 PHI 节点列表是无序的，对于有数千个前驱的 Block（如异常处理
中的 unwind block），遍历这个列表成了编译时间的瓶颈。Block Arguments
天然有序，不存在此问题。

**5. 支持"仅在某条边上存在"的值**

LLVM 的 ``invoke`` 指令无法直接表达"异常值仅在异常边上可用"——
它需要 ``landingpad`` 这种 hack。MLIR 的 Block Arguments 天然支持
这种场景：不同的前驱 Block 可以传递不同数量的参数。

.. code-block:: text

   // MLIR 中不同前驱可以传递不同的值
   ^successor(%normal_val: i32):   // 正常路径传 i32
     ...
   ^successor(%exception_val: f64): // 异常路径传 f64
     ...

.. admonition:: 不只是 MLIR 的选择
   :class: note

   Swift 的 SIL 中间表示也采用了 Block Arguments 而非 PHI 节点。
   Chris Lattner 在 2015 年 LLVM 开发者大会的演讲中详细讨论了
   这种设计的优势（见 `YouTube <https://www.youtube.com/watch?v=Ntj8ab-5cvE>`__，
   从 9:56 开始）。

Dialect 的互操作性
======================

不同的 Dialect 可以共存于同一个 MLIR 模块中：

.. code-block:: text

   // 一个混合 Dialect 的程序
   func.func @main(%A: tensor<4x4xf32>, %B: tensor<4x4xf32>)
       -> tensor<4x4xf32> {
       // linalg 级别的矩阵乘法
       %C = linalg.matmul ins(%A, %B: tensor<4x4xf32>, tensor<4x4xf32>)
           outs(%A: tensor<4x4xf32>) -> tensor<4x4xf32>
       func.return %C : tensor<4x4xf32>
   }

混合 Dialect 的模块通过 **Dialect Conversion** 逐步降级——先将 linalg 降到 scf，
再将 scf 降到 cf/arith，最后将 arith 降到 LLVM Dialect。

MLIR 的基础构建块
======================

MLIR 的所有 Dialect 都基于以下四个核心概念：

.. list-table:: MLIR 核心构建块
   :header-rows: 1

   * - 概念
     - 说明
     - 类比 LLVM IR
   * - **Operation**
     - 指令（包括算术、控制流、函数定义等一切）
     - ``Instruction``
   * - **Value**
     - SSA 值，从一个 Operation 流向另一个
     - ``Value`` / ``Use``
   * - **Block**
     - 有序的 Operation 序列，以终止操作结尾
     - ``BasicBlock``
   * - **Region**
     - 一个或多个 Block 的容器
     - （无直接对应，≈ 函数体）

这些概念构成了所有 Dialect 的基础。我们将在第 2 章中深入每个概念。

MLIR 的哲学总结
====================

.. code-block:: text

   1. 渐进降级：不是一步到位，而是逐步降低抽象级别
   2. 第一类 Dialect：用户可定义自己的 IR，与内置 IR 地位平等
   3. ODS 驱动：用 TableGen 描述 Operation，自动生成 C++ 代码
   4. SSA 风格：基于 SSA 的 Value 传递，但允许 Region 内自定义
   5. 可插拔 Pass：优化 Pass 可以在任意抽象级别上定义和运行
   6. 降级至 LLVM：最终可以到达 LLVM Dialect，利用 LLVM 后端

从源码看 Operation 的递归结构
======================================

"一切皆 Operation" 不只是一个概念，它在源码中有精确的实现。
`Operation.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Operation.h>`__
的注释详细描述了 Operation 的内存布局：

.. code-block:: text

   An Operation may optionally contain one or multiple Regions, stored in a
   tail allocated array. Each Region is a list of Blocks. Each Block is
   itself a list of Operations. This structure is effectively forming a tree.

翻译成代码就是：

.. code-block:: text

   Operation
   ├── Region (0 或多个)
   │   ├── Block
   │   │   ├── Operation
   │   │   │   ├── Region ...
   │   │   │   └── ...
   │   │   └── Operation
   │   └── Block
   └── ...

这个 **递归树结构** 是 MLIR 最核心的设计决策之一：

- **LLVM 的方式** ：Module → Function → BasicBlock → Instruction， **每层是不同类**
- **MLIR 的方式** ：Operation 包含 Region，Region 包含 Block，Block 包含 Operation， **递归统一**

这种设计的直接好处是：通用的 IR 遍历、匹配、替换工具可以 **递归地** 处理
任意深度的嵌套结构，而不需要为每种层级单独写一套 API。

设计决策：符号与类型的分离
======================================

`Rationale.md <file:///workspace/llvm-project/mlir/docs/Rationale/Rationale.md>`__
中记录了一个重要的设计决策——**类型中不允许使用符号**\ （symbols）。

当一个 tensor 或 memref 的维度在编译期未知时，用 ``?`` 表示，实际的
维度值通过 SSA 值在运行时查询：

.. code-block:: text

   // 类型中不嵌入符号：? 表示动态维度
   %A = memref.alloc <8x?xf32> (%N)
   %dim = memref.dim %A, 1 : memref<8x?xf32>

   // 不采用的方式：在类型中嵌入符号
   // (MLIR 设计决策：不这样做)
   // %A : memref<8x%Nxf32>

之所以选择前者，是因为 **类型在符号值改变时仍保持不可变** ，这简化了
类型系统的设计和实现。如果允许 ``memref<8x%Nxf32>`` ，那么当 ``%N``
的值变化时，整个类型系统都需要处理"类型随符号变化"的问题。

这是 MLIR 设计哲学中"务实"的体现： **在表达力和实现复杂度之间，MLIR
倾向于选择更简单的实现** ，即使这意味着某些信息需要在运行时查询。

源码走读：Dialect 注册与操作命名
======================================

上一节列出了 MLIR 的四大构建块，它们在源码中的落点非常集中。

**Operation** 的命名规则直接编码了 Dialect 归属。 ``Operation.h`` 中的注释说明：
如果操作名包含 ``.`` ，点号前是 Dialect 名，点号后是操作名
（`Operation.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Operation.h>`__）。
这就是为什么 ``scf.for`` 和 ``arith.addi`` 不需要额外的"所属方言"字段——
名字本身就携带了类型信息。

**Dialect** 则是 Operation 的"命名空间"和行为容器。
``Dialect.h`` 将其定义为"一组 MLIR 操作、类型和属性，以及整个组关联的行为"
（`Dialect.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Dialect.h>`__）。
每个 Dialect 可以向框架注册：

- 自定义操作的解析/打印逻辑
- 常量折叠、DCE 等接口
- 与其他 Dialect 的 Lowering 模式

这种设计让"内置 Dialect"和"用户 Dialect"走同一套注册路径——
第一类 Dialect 不是口号，而是 `DialectRegistry` 里的平等条目。

**ODS 的"轻量级"哲学** ——有了 Dialect 和 Operation 的框架，那如何
定义具体的 Operation？`OpDefinition.h <file:///workspace/llvm-project/mlir/include/mlir/IR/OpDefinition.h>`__
的文件头注释给出了答案：

.. code-block:: cpp

   /// The purpose of these types are to allow light-weight implementation
   /// of concrete ops (like DimOp) with very little boilerplate.

这个"light-weight implementation"（轻量级实现）是 MLIR 设计哲学中
"务实"的另一个体现。在 ``.td`` 文件中用 ODS 声明式地描述 Operation：

.. code-block:: tablegen

   def AddIOp : Op<"arith.addi"> {
     let summary = "integer addition operation";
     let arguments = (ins AnyInteger:$lhs, AnyInteger:$rhs);
     let results = (outs AnyInteger:$result);
   }

ODS 会自动生成 C++ 的 ``AddIOp`` 类，开发者无需手写 ``class`` 定义、
``parse``/``print`` 方法、 ``verify`` 逻辑——这些全部从声明中推导。
这种"声明式规范，自动生成实现"的模式贯穿 MLIR 的整个设计。

渐进降级在源码中的体现
==============================

降级不是某个单一函数完成的，而是 **一串 Pass** 串联而成。
以 ``scf.for`` → 控制流图为例， ``SCFToControlFlow.cpp`` 的文件头注释
写得很直白：这个 Pass 将 ``scf.for`` 、 ``scf.if`` 转换为标准 CFG 操作
（`SCFToControlFlow.cpp <file:///workspace/llvm-project/mlir/lib/Conversion/SCFToControlFlow/SCFToControlFlow.cpp>`__）。

文件中用 ASCII 图详细描述了降级后 CFG 的结构——条件块、循环体块、出口块
如何拼接。读懂这段注释，就理解了为什么上一节的 ``scf.for`` 示例
在降级后会变成 ``cf.br`` / ``cf.cond_br`` 的组合。

这与第一卷 :ref:`chapter-04-03-new-pm` 讨论的 Pass Pipeline 思想一脉相承：
MLIR 的 ``PassManager`` 同样按序调度变换，只不过操作对象从 ``llvm::Function``
变成了 ``mlir::Operation`` 。

动手验证
==========

用 MLIR 打印一个混合 Dialect 的模块，观察操作命名：

.. code-block:: console

   cat > /tmp/mixed.mlir << 'EOF'
   func.func @main(%a: i32, %b: i32) -> i32 {
     %sum = arith.addi %a, %b : i32
     func.return %sum : i32
   }
   EOF
   mlir-opt /tmp/mixed.mlir

输出中 ``func.func`` 、 ``arith.addi`` 、 ``func.return`` 分属三个 Dialect，
却共存于同一模块——这正是"第一类 Dialect"的实际表现。

本章小结
========

MLIR 的设计哲学可以归结为一句话： **在正确的抽象层次做正确的事** 。
渐进降级保证每层 IR 都保留足够的语义；第一类 Dialect 保证任何人都能
在框架上搭建自己的 IR 层。

带着这些原则，下一章 :ref:`mlir-02-index` 将逐一拆解
Operation、Value、Block、Region 四大构建块。


.. rubric:: 进一步阅读

- `MLIR 官方文档 <https://mlir.llvm.org/docs/>`_ — MLIR 的所有指南和 Rationale
- Chris Lattner 在 2019 LLVM Dev Meeting 的演讲：*MLIR: Compiler Infrastructure for End of Moore's Law*
- `MLIR 论文 <https://arxiv.org/abs/1902.08068>`_ — *MLIR: Scaling Compiler Infrastructure for Domain Specific Computation*


*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm · 第二卷 MLIR*
