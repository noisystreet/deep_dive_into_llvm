.. _appendix-03-glossary:

==========================
术语表
==========================

.. glossary::

   SSA (Static Single Assignment)
      静态单赋值形式。LLVM IR 的核心属性之一，每个变量只被赋值一次，
      简化了数据流分析和优化。

   BasicBlock
      基本块。LLVM IR 中的基本控制流单元，具有单一入口和单一出口，
      以 terminator instruction 结尾。

   Pass
      在 LLVM 中，Pass 是对 IR 进行分析或变换的操作单元。

   SelectionDAG
      LLVM 后端代码生成阶段使用的有向无环图表示，将 MachineInstr 抽象为 DAG 节点。

   TableGen
      LLVM 中的声明式代码生成工具，用于描述指令集、寄存器等目标机器信息。

   GEP (GetElementPtr)
      LLVM IR 中的地址计算指令，用于计算聚合类型（结构体、数组）中元素的地址。

   LTO (Link-Time Optimization)
      链接时优化，在链接阶段对整个程序进行优化分析。

   ThinLTO
      一种增量式 LTO 方案，在保持 LTO 大多数优化收益的同时显著降低构建时间。

   Alias Analysis
      别名分析，判断两个内存访问是否可能指向同一内存位置的分析技术。

   Induction Variable
      归纳变量，在循环中每次迭代以固定值递增的变量，循环优化的关键分析对象。

   Loop Invariant Code Motion (LICM)
      将循环体内不随迭代变化的计算外提到循环外部的优化。

   InlineCost
      内联代价分析，衡量函数内联的代码膨胀成本 vs. 性能收益。

   MC Layer
      Machine Code 层，提供与具体目标格式（ELF/MachO/COFF）无关的
      汇编和对象文件生成接口。

   ORC JIT
      LLVM 的下一代 JIT 编译框架，提供分层的、异步的、可组合的 JIT 基础设施。

   Polly
      LLVM 中的多面体优化框架，用于对循环嵌套进行高级的依赖分析和变换。

   Sanitizer
      LLVM 提供的一系列动态分析工具，包括 AddressSanitizer、UndefinedBehaviorSanitizer、ThreadSanitizer 等。

   Intersphinx
      Sphinx 扩展，允许在不同项目的文档之间创建交叉引用链接。

   Autosectionlabel
      Sphinx 扩展，自动为文档中的每个章节生成可引用的标签。
