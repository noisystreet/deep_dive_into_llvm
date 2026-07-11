.. _appendix-03-glossary:

==========================
术语表
==========================

.. glossary::

   Alias Analysis
      别名分析，判断两个内存访问是否可能指向同一内存位置的分析技术。

   arith (MLIR Dialect)
      MLIR 中定义基本算术运算的 Dialect，包括 ``addi``、``subi``、``muli``、
      ``divf`` 等整数和浮点运算，是渐进降级路径中的底层标量 Dialect。

   Attribute (MLIR)
      MLIR 中附着在 Operation 上的静态元数据，如常量值、维度信息、接口实现。
      与 LLVM 的 metadata 类似，但 MLIR 的 Attribute 是类型化的、可唯一化的。

   Autosectionlabel
      Sphinx 扩展，自动为文档中的每个章节生成可引用的标签。

   BasicBlock
      基本块。LLVM IR 中的基本控制流单元，具有单一入口和单一出口，
      以 terminator instruction 结尾。

   Block (MLIR)
      MLIR 中一个有序的 Operation 序列，以终止操作（terminator）结尾。
      Block 可以有参数（Block Arguments），用于从控制流前驱接收值。

   Block Arguments (MLIR)
      MLIR 中 Block 的入口参数，用于从前驱 Block 传递值。与 LLVM 的 PHI 节点
      语义等价，但更简洁：函数参数是入口 Block 的参数，循环携带值通过
      ``iter_args`` 表示。

   builtin (MLIR Dialect)
      MLIR 的内置 Dialect，定义了所有 MLIR 程序都需要的核心类型和操作，
      如 ``ModuleOp``、``func.func``、整数类型、浮点类型等，无需显式导入。

   CFG (Control Flow Graph)
      控制流图，以基本块为节点、控制流边为有向边的图结构，是编译器进行
      控制流分析和变换的基础数据结构。

   Clang
      LLVM 的 C/C++/Objective-C 前端编译器，将源码解析为 AST 后生成 LLVM IR。
      以编译速度快、错误信息清晰、模块化设计著称。

   compiler-rt
      LLVM 子项目，提供编译器所需的运行时支持函数，包括软浮点模拟
      （``__addsf3``）、地址消毒剂（AddressSanitizer）、覆盖率检测等。

   DAGCombine
      SelectionDAG 层面的优化过程，在指令选择前对 DAG 做目标无关的优化，
      如消除冗余操作（``add x, 0 → x``）、合并模式等。

   Debug Info (LLVM IR)
      LLVM IR 中的调试信息元数据，采用 ``!dbg`` 标签和 ``DILocalVariable``、
      ``DISubprogram`` 等调试元数据节点，支持源代码级调试。

   Dialect (MLIR)
      MLIR 中一组 Operation、Type、Attribute 的集合，构成一个独立的"迷你 IR"。
      每个 Dialect 拥有自己的命名空间（如 ``arith.``、``scf.``），
      通过 Dialect Registry 注册到 MLIRContext 中。

   Dialect Conversion (MLIR)
      MLIR 中将一个 Dialect 的 Operation 转换为另一个 Dialect 的过程，
      是渐进降级（Progressive Lowering）的核心机制。通常通过 Pattern Rewrite
      实现，将高层 Operation 匹配替换为低层 Operation 的组合。

   Dominator Tree
      支配树，表示基本块之间的支配关系。若从入口到 Block B 的每条路径都经过
      Block A，则 A 支配 B。用于优化（如 LICM 判断循环不变量）和分析。

   Function (LLVM IR)
      LLVM IR 中的函数定义，包含函数签名（返回类型、参数列表）和函数体
      （BasicBlock 列表）。在 ``llvm::Function`` 类中实现。

   GEP (GetElementPtr)
      LLVM IR 中的地址计算指令，用于计算聚合类型（结构体、数组）中元素的地址。
      不访问内存，仅做指针算术，步长由类型系统推导。

   GlobalISel
      LLVM 后端的第二代指令选择框架，采用渐进降级方式：先将 IR 翻译为
      泛型 MachineInstr，再通过多次 Legalization 和 Combine 逐步降低到
      目标特定指令。

   GVN (Global Value Numbering)
      全局值编号，一种识别冗余表达式的优化技术。通过为每个值分配全局唯一
      编号，发现并消除计算相同值的重复指令。

   Induction Variable
      归纳变量，在循环中每次迭代以固定值递增的变量，循环优化的关键分析对象。

   InlineCost
      内联代价分析，衡量函数内联的代码膨胀成本 vs. 性能收益。

   InstCombine
      LLVM 中最重要的优化 Pass 之一，基于模式匹配的指令级简化。它将指令
      替换为语义等价但更高效的形式，如 ``(X | Y) & X → X``。

   Instruction (LLVM IR)
      LLVM IR 中的单条指令。每条 Instruction 有操作码（opcode）、操作数
      （operands）和结果类型。在 ``llvm::Instruction`` 类中实现。

   Instruction Selection
      指令选择，将目标无关的 SelectionDAG 或 GlobalISel 泛型指令匹配为
      目标架构的原生指令。核心逻辑由 TableGen 生成的匹配表驱动。

   Intersphinx
      Sphinx 扩展，允许在不同项目的文档之间创建交叉引用链接。

   JIT Compilation
      即时编译（Just-In-Time），在运行时将代码编译为机器码的技术。
      LLVM 提供 MCJIT 和 ORC JIT 两代 JIT 引擎。

   Legalization
      合法化，将 SelectionDAG 或 GlobalISel 中目标架构不支持的操作/类型
      转换为原生支持的形式。包括类型合法化（如拆分 i128）和操作合法化
      （如将乘法展开为移位/加法）。

   linalg (MLIR Dialect)
      MLIR 中定义线性代数操作的 Dialect，如 ``matmul``、``conv``、``fill`` 等。
      位于渐进降级路径的中层，介于结构化控制流（scf）和底层原语（arith/memref）之间。

   LLD
      LLVM 子项目，从零实现的链接器，比传统 GNU ld 快数倍。支持 ELF、COFF、
      Mach-O、WebAssembly 等多种目标文件格式。

   LLDB
      LLVM 子项目，基于 LLVM 和 Clang 构建的调试器，使用 Clang 解析表达式、
      LLVM 底层 API 处理调试信息。相比 GDB 启动更快、内存占用更低。

   LLJIT
      ORC JIT 框架中的核心 JIT 类，提供开箱即用的 JIT 编译能力，支持
      增量编译、懒编译、多 JIT 实例共存。

   llc
      LLVM 的静态编译器后端工具，将 LLVM IR 编译为目标文件或汇编代码。
      支持通过 ``-stop-after`` 观察 CodeGen 各阶段的中间状态。

   lli
      LLVM 的 JIT 执行工具，可以直接执行 LLVM IR 或比特码文件，无需
      编译为目标文件。支持 MCJIT 和 ORC JIT 两种后端。

   Loop Vectorization
      循环向量化，将标量循环转换为使用 SIMD 指令的向量化形式。LLVM 提供
      Loop Vectorizer（处理结构化循环）和 SLP Vectorizer（处理基本块内
      的冗余指令）。

   LTO (Link-Time Optimization)
      链接时优化，在链接阶段对整个程序进行优化，跨越编译单元边界。
      LLVM 支持 Full LTO 和 ThinLTO 两种模式。

   MC Layer
      Machine Code 层，提供与具体目标格式（ELF/MachO/COFF）无关的
      汇编和对象文件生成接口。

   MCJIT
      LLVM 的第一代 JIT 引擎（2013 年引入），在模块级别编译 LLVM IR。
      已被 ORC JIT 取代，目前处于维护模式。

   memref (MLIR)
      MLIR 中表示内存缓冲区的类型，包含数据类型、维度信息（静态或动态）
      和内存布局映射。类似 C 语言的多维数组，但支持仿射映射表达的
      非标准内存布局。

   MLIR (Multi-Level Intermediate Representation)
      多层中间表示，LLVM 子项目（2019 年发布），是一套可定义任意多层 IR
      的编译器基础设施框架。核心设计：Dialect 机制 + 渐进降级。

   MLIRContext
      MLIR 的顶层容器，管理所有 Dialect 注册、类型/属性唯一化、多线程
      调度。在 MLIR 中扮演"操作系统"的角色，所有 IR 的创建和操作都
      依赖于 Context。

   Module (LLVM IR)
      LLVM IR 的顶层容器，包含函数定义、全局变量、目标信息等。一个
      Module 对应一个翻译单元。在 ``llvm::Module`` 类中实现。

   ODS (Operation Definition Spec)
      MLIR 的声明式 Operation 定义规范，基于 TableGen 的 ``.td`` 文件。
      开发者只需声明操作数、结果、属性等，ODS 自动生成 C++ 类、
      parse/print/verify 代码。

   Opaque Pointer
      LLVM 15+ 引入的指针类型简化，用 ``ptr`` 替代 ``i32*``、``i8*`` 等
      带类型的指针。指针的类型信息通过 ``load``/``store`` 指令的另一个
      操作数来携带。

   Operation (MLIR)
      MLIR 中一切执行的基本单元。一条算术指令、一个函数定义、一个循环、
      整个模块都是 Operation。Operation 可以包含 Region，形成递归树结构。

   opt
      LLVM 的 IR 优化工具，可以加载并运行指定的 Pass Pipeline。
      用于调试和验证优化 Pass 的效果，支持 ``-passes=`` 指定 Pass 序列。

   ORC JIT
      LLVM 的下一代 JIT 编译框架，提供分层的、异步的、可组合的 JIT 基础设施。

   Pass
      在 LLVM 中，Pass 是对 IR 进行分析或变换的操作单元。LLVM 有 Legacy PM
      和 New PM 两套 Pass 管理框架。

   Pass Pipeline
      Pass 的执行管道，由多个 Pass 按特定顺序排列而成。LLVM 预定义了
      -O0 到 -Oz 等优化等级对应的 Pipeline，也支持用户自定义。

   Pattern Rewrite (MLIR)
      MLIR 的声明式 IR 变换框架，定义"源模式 → 目标模式"的匹配-替换规则。
      支持在 Dialect 内做优化，也支持跨 Dialect 的降级转换。

   PHI Node
      LLVM IR 中用于表示 SSA 控制流汇合的指令，位于 BasicBlock 顶部。
      MLIR 使用 Block Arguments 替代 PHI 节点，语义等价但更简洁。

   Polly
      LLVM 中的多面体优化框架，用于对循环嵌套进行高级的依赖分析和变换。

   Progressive Lowering (MLIR)
      渐进降级，MLIR 的核心设计哲学之一。不要求从源语言一步降到机器码，
      而是通过多层 Dialect 逐步降低抽象级别，每层在合适的粒度上做优化。

   Register Allocation
      寄存器分配，将虚拟寄存器（virtual register）映射到物理寄存器
      ／栈内存。LLVM 使用 Greedy Register Allocator，基于活跃性分析
      做全局分配。

   Sanitizer
      LLVM 提供的一系列动态分析工具，包括 AddressSanitizer、
      UndefinedBehaviorSanitizer、ThreadSanitizer 等。

   ScalarEvolution (SCEV)
      LLVM 的分析 Pass，对循环内整数表达式做闭式分析，推导归纳变量的
      变化规律（如 ``{0,+,1}<loop>`` 表示从 0 开始、步长为 1 的序列）。

   scf (MLIR Dialect)
      MLIR 中定义结构化控制流的 Dialect，包括 ``scf.for``\ （循环）、
      ``scf.if``\ （条件分支）、``scf.while``\ （不定循环）。使用 Region
      表示循环体，保留了循环结构信息。

   SelectionDAG
      LLVM 后端代码生成阶段使用的有向无环图表示，将 MachineInstr 抽象为 DAG 节点。

   SLP Vectorizer
      Superword-Level Parallelism 向量化器，在基本块内寻找语义等价的
      独立标量指令，将其合并为向量指令。与 Loop Vectorizer 互补。

   SSA (Static Single Assignment)
      静态单赋值形式。LLVM IR 的核心属性之一，每个变量只被赋值一次，
      简化了数据流分析和优化。

   StableHLO
      MLIR 生态中的机器学习计算图 Dialect，由 TensorFlow 和 JAX 社区
      共同维护，作为 ML 框架之间的互通 IR。

   TableGen
      LLVM 中的声明式代码生成工具，用于描述指令集、寄存器等目标机器信息。

   TargetMachine
      LLVM 中代表目标架构的类，封装了目标特定的指令选择、寄存器分配、
      指令调度等信息。每个后端（X86、ARM、RISC-V 等）有对应的
      TargetMachine 子类。

   tensor (MLIR)
      MLIR 中表示张量的类型，是多维数组的抽象表示。tensor 与 memref 的
      区别在于：tensor 是不可变的 SSA 值，而 memref 是可变的缓冲区。

   Terminator
      终止操作，位于 Block 末尾的 Operation，决定控制流去向。如 LLVM 的
      ``br``、``ret``，MLIR 的 ``scf.yield``、``cf.br``。

   ThinLTO
      一种增量式 LTO 方案，在保持 LTO 大多数优化收益的同时显著降低构建时间。

   TOSA
      MLIR 生态中的机器学习算子 Dialect（Tensor Operator Set Architecture），
      定义了一套标准化的推理引擎算子集，用于跨框架的模型部署。

   Value (MLIR)
      MLIR 中 SSA 值的抽象，由 Operation 产生或被 Block 参数定义。
      每个 Value 有类型和 def-use 链，是数据流分析的基础。