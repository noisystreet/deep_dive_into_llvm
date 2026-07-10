.. _mlir-01-01-01:

=============
什么是 MLIR？
=============

如果你读完了本书的第一卷，你已经熟悉了 LLVM IR——一种语言无关的、基于 SSA 的
中间表示。LLVM IR 成功地统一了编译器前端的多样性和后端的多样性： **无论你用什么
语言（C、C++、Rust、Swift），无论你 targeting 什么架构（x86、ARM、RISC-V），
都可以用 LLVM IR 作为桥梁** 。

但 LLVM IR 有一个根本性的局限。

.. admonition:: MLIR 的诞生：一场 Google 内部的"IR 起义"
   :class: note

   2019 年 4 月，LLVM 开发者大会上出现了一个引人注目的新项目：
   **MLIR（Multi-Level Intermediate Representation）** 。但它的故事
   早在 2017 年就开始了。

   当时 Google 的 TensorFlow 团队面临一个头疼的问题：TensorFlow 的
   计算图需要通过 XLA 编译器编译到 GPU/TPU，而 XLA 内部使用的 HLO IR
   （High-Level Operations）和 LLVM IR 之间存在着巨大的 **语义鸿沟** 。
   为了填补这道鸿沟，Google 团队在 LLVM IR 之上堆了 **多层** 自定义的
   IR 转换——结果就是代码越来越复杂、维护越来越困难。

   Chris Lattner 在 2017 年加入 Google 后，很快就意识到问题的根源：
   **不是 IR 不够好，而是 IR 的数量不够多** 。传统编译器的架构假设
   "一个 IR 就够了"，但现实中，不同的优化需要不同抽象层次的 IR。
   他的解决方案很大胆：为什么不做一个 **可以定义任意多 IR** 的框架？

   这就是 MLIR 的核心理念——一个 **IR 的 IR 框架** 。你不是在使用一个
   固定的 IR，而是使用 MLIR 的 Infrastructure 来 **创造自己需要的 IR** 。
   每个 IR 被称作一个 Dialect，而 Dialect 本身也是 MLIR 中的一等公民。

   有趣的是，LLVM 社区内部一开始对这个项目持保留态度——"又一个 IR？"
   "为什么不能在 LLVM IR 上改进？" 但 Lattner 在 2019 年 LLVM 开发者
   大会上的演讲 *"MLIR: A Compiler Infrastructure for the End of Moore's Law"*
   改变了很多人看法。他展示了 MLIR 如何将 TensorFlow 的 100 多种操作
   通过逐层降级，最终生成高效的 LLVM IR——整个过程完全模块化、可组合、
   可验证。

   今天，MLIR 已经成为 LLVM 生态中增长最快的子项目之一。

.. rst-class:: center

   LLVM IR 是"最底层"的 IR——它离机器码很近，离源代码很远。
   如果要在 LLVM IR 上做高级优化（如循环分块、内存融合），你需要
   先将近乎源码级的信息从 IR 中"反向推导"出来。

传统编译器的 IR 困境
==========================

.. mermaid::

   flowchart LR
       A["Python / Julia / ML 框架模型"] --> B[高级语言语义]
       B --> C[LLVM IR]
       C --> D[机器码]

       style B fill:#e91e63,color:#fff
       style C fill:#ff9800,color:#fff
       style D fill:#4caf50,color:#fff

在 LLVM IR 成为行业标准之后，出现了一些新的需求，LLVM IR 难以很好支持：

**1. 高级抽象的缺失**

LLVM IR 是低级 IR——它没有 ``for`` 循环、没有张量（tensor）、没有多维数组的概念。
如果你想优化一个矩阵乘法，在 LLVM IR 层面你看不到"矩阵"——你只看到一堆
``load`` 、 ``store`` 、 ``add`` 、 ``mul`` 指令。你需要通过模式匹配来"猜测"
源代码的结构。

**2. 降级（Lowering）过程中的信息丢失**

当 Clang 将 ``for (int i = 0; i < n; i++)`` 编译为 LLVM IR 时，它变成了
``phi`` 、 ``icmp`` 、 ``br`` 指令的组合——循环结构信息丢失了。之后想恢复这个
信息做循环优化，需要运行 ``LoopInfo`` 分析 Pass 重新推导。

**3. 多种 IR 之间的转换成本**

在一个复杂系统中（如 TensorFlow 的 XLA 编译器、Julia 的编译器），同一个程序
可能需要经过多个不同层次的 IR：源码 AST → 高级中间表示 → 中端 IR → LLVM IR →
机器码。每次转换都需要编写和维护转换代码。

MLIR 的诞生
================

MLIR（Multi-Level Intermediate Representation）是 LLVM 项目中为了解决上述问题
而发起的新项目。它在 2019 年的 LLVM 开发者大会上首次公开发布，由 Google、Apple
等公司的工程师共同推动。

MLIR 的核心思想很简单： **不要试图用一个 IR 覆盖所有需求，而是让用户定义
自己需要的 IR** 。

.. mermaid::

   flowchart LR
       A["Python / ML 框架模型"] --> B["HLO / TOSA\n（高级操作数）"]
       B --> C["linalg / scf\n（结构化控制流）"]
       C --> D["arith / memref\n（底层原语）"]
       D --> E["LLVM Dialect\n（LLVM IR 映射）"]
       E --> F[机器码]

       style A fill:#e91e63,color:#fff
       style F fill:#4caf50,color:#fff

这就是 **Progressive Lowering** （渐进降级）的哲学：不是一步跳到 LLVM IR，
而是通过多个层次的 IR，逐步降低抽象级别。每一层都在合适的抽象级别上做优化。

MLIR 不是一种 IR
=====================

MLIR 官方的定位是："MLIR is not a particular IR——it's an infrastructure for
building and working with IRs。"

这意味着：

- MLIR 提供了一 **套框架** 来定义 IR（Operation、Type、Attribute、Dialect）
- 你可以用 MLIR 框架定义自己需要的 IR（称为 **Dialect** ）
- 不同 Dialect 之间可以互相转换（通过 Lowering Pass）
- 最终可以降级到 LLVM Dialect，然后翻译为 LLVM IR，接着走 LLVM 后端的代码生成

.. code-block:: text

   MLIR Framework（基础设施层）
   ├── Operation / Value / Block / Region（基本构造块）
   ├── Dialect 注册机制
   ├── Type / Attribute 系统
   ├── Pass 框架 / Pattern Rewrite 系统
   ├── ODS（Operation Definition Spec）
   └── 文件 I/O（.mlir 格式）

   User-defined Dialects（用户定义的方言）
   ├── builtin（内置基础方言）
   ├── func / arith / math / scf / cf
   ├── tensor / linalg / memref
   ├── LLVM Dialect
   ├── TOSA / StableHLO（机器学习）
   └── 你自己定义的 Dialect

MLIR 命名中的"多重含义"
==============================

"MLIR" 这四个字母到底代表什么？官方的 `Rationale.md <file:///workspace/llvm-project/mlir/docs/Rationale/Rationale.md>`__
开篇就给出了一个坦诚的回答：

.. code-block:: text

   MLIR stands for one of "Multi-Level IR" or "Multi-dimensional Loop IR"
   or "Machine Learning IR" or "Mid Level IR" — we prefer the first.

**官方首选的是 "Multi-Level IR"** （多级中间表示），因为这个名字最准确地
反映了 MLIR 的核心设计：不只有一种 IR，而是有 **多层 IR** ，每层在不同的
抽象级别上工作。

至于其他几个候选名字也各有渊源：
- **Multi-dimensional Loop IR** ：点出了 MLIR 的多面体编译（polyhedral）基因
- **Machine Learning IR** ：反映了 MLIR 最初的驱动场景（TensorFlow/XLA）
- **Mid Level IR** ：强调了它在编译流程中的"中端"定位

这种"名字不止一个含义"的模糊性，恰恰说明了 MLIR 的定位——它不是一个
为单一目的设计的 IR，而是一个 **框架** ，不同的使用者看到不同的侧面。

多面体编译的基因
========================

MLIR 不仅继承了 LLVM 的 SSA 传统，还吸收了 **多面体编译** （polyhedral
compilation）的核心思想。`Rationale.md <file:///workspace/llvm-project/mlir/docs/Rationale/Rationale.md>`__
中这样描述：

.. code-block:: text

   MLIR 是一种混合设计：结合了传统三地址 SSA 表示与多面体循环优化
   表示中的概念，旨在表达、分析和变换高层数据流图以及面向高性能
   数据并行系统的目标代码。

多面体模型用 **整数映射、集合和关系** 来描述循环嵌套和多维数组访问。
这使得 MLIR 能够以 **数学形式** 紧凑地表达循环分块、循环融合、循环交换
等所有传统循环变换，而不需要像 LLVM IR 那样先通过 ``LoopInfo`` 分析
"逆向推导"循环结构。

与 LLVM 的 Polly 项目不同，Polly 只能处理满足仿射约束的"规则"循环，
MLIR 的设计允许 **不规则控制流和数据访问** 与多面体表示共存——只不过
不规则部分无法应用多面体优化，但不影响 IR 的合法性。

MLIR 与 LLVM IR 的对比
==============================

.. list-table:: MLIR vs LLVM IR
   :header-rows: 1

   * - 特征
     - LLVM IR
     - MLIR
   * - 抽象层次
     - 单一低级 IR
     - 多层 IR（从高级到低级）
   * - IR 定义
     - 固定（由 LLVM 定义）
     - 可扩展（用户定义 Dialect）
   * - 类型系统
     - 固定基本类型（i32, ptr, ...）
     - 可扩展（用户定义 Type）
   * - 操作集
     - 固定（add, load, store, ...）
     - 可扩展（用户定义 Operation）
   * - SSA 形式
     - 强制
     - 可选（Dialect 自行决定）
   * - 优化
     - 统一优化 Pass
     - Dialect 专属优化 + 跨 Dialect 降级
   * - 主要用途
     - 传统编译器的 IR
     - 编译器框架 + 机器学习编译器

MLIR 不是要取代 LLVM，而是 **建立在 LLVM 之上的抽象层** 。MLIR 的最后一层
（LLVM Dialect）可以精确映射为 LLVM IR，然后继续走 LLVM 的优化和代码生成。

同一函数，两种 IR 长什么样？
==================================

光看对比表还不够直观。下面这个求和函数，帮你看清 MLIR 和 LLVM IR 的抽象差异。

**MLIR（scf + arith，保留循环结构）**

.. code-block:: text

   func.func @sum(%n: index) -> i32 {
     %c0 = arith.constant 0 : i32
     %c1 = arith.constant 1 : index
     %result = scf.for %i = %c0 to %n step %c1
         iter_args(%acc = %c0) -> i32 {
       %next = arith.addi %acc, %i : i32
       scf.yield %next : i32
     }
     func.return %result : i32
   }

优化器一眼就能看出：这是一个带归纳变量的循环， ``%acc`` 是循环携带值（loop-carried value）。
在 ``linalg`` 或 ``tensor`` 层次，你甚至能看到"矩阵乘法"这样的高层语义——不必从 ``load/add`` 反推。

**LLVM IR（phi + br，循环结构需分析恢复）**

.. code-block:: text

   define i32 @sum(i64 %n) {
   entry:
     br label %cond
   cond:
     %i = phi i64 [ 0, %entry ], [ %i.next, %body ]
     %acc = phi i32 [ 0, %entry ], [ %acc.next, %body ]
     %cmp = icmp slt i64 %i, %n
     br i1 %cmp, label %body, label %exit
   body:
     %acc.next = add i32 %acc, %i
     %i.next = add i64 %i, 1
     br label %cond
   exit:
     ret i32 %acc
   }

这段 IR 在语义上等价，但"循环"已经变成了 ``phi``/``br`` 的组合。
要做循环分块或向量化，编译器得先跑 ``LoopInfo`` 分析把结构找回来——这正是
:ref:`chapter-05-03-loop-optimizations` 中讨论的问题。

MLIR 的做法不是抛弃 LLVM IR，而是在它 **上方** 再铺几层语义更丰富的 IR，
让每一层都在合适的粒度上做优化，最后再降到 LLVM IR 走成熟的后端。
这与第一卷 :ref:`chapter-07-01-backend-overview` 描述的 CodeGen 管道形成上下衔接。

谁在用 MLIR？
====================

- **TensorFlow / JAX** ：使用 MHLO / StableHLO 作为 ML 编译器的前端 IR
- **PyTorch** ：PyTorch 2.0 的 torch.compile 使用 MLIR 作为中间表示
- **Julia** ：使用 MLIR 进行高性能科学计算
- **CIRCT** （Circuit IR Compilers and Tools）：用 MLIR 做硬件设计和 EDA
- **Polygeist** ：将 C/C++ 转换为 MLIR，结合 Polyhedral 优化

源码走读：MLIR 框架的入口
==============================

MLIR 所有 Dialect 的操作最终都建立在 ``Operation`` 类之上。源码注释直接点明了
它的角色——"MLIR 中执行的基本单元"：

`mlir/include/mlir/IR/Operation.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Operation.h>`__

其中有一段关键说明：操作名如果包含 ``.`` ，点号前面是 Dialect 名，后面是操作名。
这就是为什么我们在 IR 中看到 ``arith.addi`` 、 ``scf.for`` 这样的命名格式——
它不是语法糖，而是 MLIR 框架对 Dialect 的 **一等公民** 支持的直接体现。

Dialect 本身的定义在 `mlir/include/mlir/IR/Dialect.h <file:///workspace/llvm-project/mlir/include/mlir/IR/Dialect.h>`__：

.. code-block:: cpp

   /// Dialects are groups of MLIR operations, types and attributes, as well as
   /// behavior associated with the entire group.

一组 Operation、Type、Attribute 加上统一的行为钩子，就构成一个 Dialect。
内置的 ``arith`` 、 ``scf`` 和你将来自定义的 Dialect，在框架眼里没有高低之分。

MLIRContext：一切的中心
==============================

所有 Dialect、Operation、Type 的"存活"离不开一个顶层容器——
`MLIRContext <file:///workspace/llvm-project/mlir/include/mlir/IR/MLIRContext.h>`__。
源码注释这样描述它：

.. code-block:: cpp

   /// MLIRContext is the top-level object for a collection of MLIR operations.
   /// It holds immortal uniqued objects like types, and the tables used to
   /// unique them.

MLIRContext 扮演着 **"MLIR 的操作系统"** 的角色：

- **Dialect 注册中心** ：所有加载的 Dialect 都注册在 Context 中
- **类型/属性的唯一化表** ：相同的类型（如 ``i32`` ）在 Context 中只存一份
- **多线程支持** ：Context 封装了线程池，可以并行处理 IR

.. code-block:: cpp

   // 创建 Context 并注册 Dialect
   MLIRContext context;
   context.getOrLoadDialect<arith::ArithDialect>();
   context.getOrLoadDialect<scf::SCFDialect>();

Context 的另一个重要设计是 **可配置的线程模式** 。注释中给出了一个典型的
使用场景：对于长时间运行、会反复创建和销毁 Context 的进程，可以显式
禁用内置线程池，注入外部线程池来避免线程爆炸：

.. code-block:: cpp

   llvm::DefaultThreadPool myThreadPool;
   while (auto *request = nextCompilationRequests()) {
     MLIRContext ctx(registry, MLIRContext::Threading::DISABLED);
     ctx.setThreadPool(myThreadPool);
     processRequest(request, ctx);
   }

这种设计让 MLIR 既能服务于一次性编译（如 ``mlir-opt`` 工具），也能服务
于长期运行的 JIT 服务（如 TensorFlow 的 XLA 编译器）。

动手验证
==========

确认本地 MLIR 工具链可用，并观察一次最简降级：

.. code-block:: console

   # 确认 mlir-opt 可用
   mlir-opt --version

   # 将 arith/func 降级到 LLVM Dialect（示例见 examples/mlir/chapter_06_lowering/）
   mlir-opt examples/mlir/chapter_06_lowering/vector_add.mlir \
       --convert-scf-to-cf \
       --convert-arith-to-llvm \
       --convert-func-to-llvm \
       --reconcile-unrealized-casts

输出中应出现 ``llvm.func`` 和 ``llvm.add``——这说明 MLIR 已经走到了
连接 LLVM 后端的最后一站。JIT 执行这条路径的细节将在
:ref:`mlir-11-11-04` 展开。

本章小结
========

本节回答了"MLIR 是什么"：它不是又一个固定 IR，而是一套 **可定义多层 IR** 的
基础设施。LLVM IR 擅长贴近机器的优化，MLIR 擅长在更高层次保留源程序的语义结构。

下一节 :ref:`mlir-01-01-02` 将深入其两大设计支柱——渐进降级与第一类 Dialect 机制。
