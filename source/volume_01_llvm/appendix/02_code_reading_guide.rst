.. _appendix-02-code-reading-guide:

==========================
代码阅读指南
==========================

LLVM 源码库庞大且组织有序。掌握正确的阅读方法，可以大大提高学习效率。

.. rst-class:: center

   LLVM 源码中最值得读的三个文件：
   ``LLVMContext.h`` 、 ``Instruction.h`` 、 ``PassManager.h`` 。

源码目录结构
==================

LLVM 项目的主仓库（ ``llvm-project`` ）采用模块化布局：

.. code-block:: text

   llvm-project/
   ├── llvm/                    # LLVM 核心
   │   ├── lib/IR/               # IR 定义（Instruction, BasicBlock, Function）
   │   ├── lib/Transforms/       # 优化 Pass（InstCombine, GVN, LICM 等）
   │   ├── lib/CodeGen/          # 代码生成（ISel, RA, Scheduling）
   │   ├── lib/Target/           # 后端目标描述（X86, ARM, RISCV 等）
   │   ├── include/llvm/IR/      # IR 头文件
   │   └── tools/                # opt, llc, lli 等工具
   ├── clang/                    # C/C++ 前端
   ├── mlir/                     # MLIR 框架
   ├── lld/                      # 链接器
   ├── lldb/                     # 调试器
   └── compiler-rt/             # 运行时库（ASan, UBSan 等）

关键子目录详解
==================

**llvm/lib/IR**——LLVM IR 的核心实现

.. code-block:: text

   llvm/lib/IR/
   ├── Type.cpp              # 类型系统
   ├── Value.cpp             # SSA 值（Value 基类）
   ├── User.cpp              # 使用值的使用者
   ├── Instruction.cpp       # 指令定义
   ├── BasicBlock.cpp        # 基本块
   ├── Function.cpp          # 函数定义
   ├── Module.cpp            # 模块（翻译单元）
   ├── Dominators.cpp        # 支配树
   └── Verifier.cpp          # IR 验证器

建议阅读顺序： ``Type → Value → User → Instruction → BasicBlock → Function → Module`` 。

**llvm/lib/Transforms**——优化 Pass

.. code-block:: text

   llvm/lib/Transforms/
   ├── InstCombine/           # 指令合并（最常修改的 Pass）
   ├── Scalar/                # 标量优化（GVN, LICM, SCCP 等）
   ├── Vectorize/             # 向量化（LoopVectorize, SLPVectorize）
   ├── IPO/                   # 过程间优化（Inliner, GlobalOpt）
   └── Utils/                 # 工具函数

**llvm/lib/CodeGen**——代码生成

.. code-block:: text

   llvm/lib/CodeGen/
   ├── SelectionDAG/          # SelectionDAG ISel
   ├── GlobalISel/            # Global ISel（较新）
   ├── RegisterAllocator.cpp  # 寄存器分配
   ├── MachineScheduler.cpp   # 指令调度
   └── AsmPrinter/            # 汇编输出

**llvm/lib/Target**——后端目标支持

.. code-block:: text

   llvm/lib/Target/
   ├── X86/                   # x86/x86-64 后端
   ├── AArch64/               # ARM 64 位后端
   ├── RISCV/                 # RISC-V 后端
   └── WebAssembly/           # Wasm 后端

推荐阅读路线
==================

根据你的学习目标，推荐的源码阅读顺序：

**路线 A：IR 与优化方向**

.. code-block:: text

   1. llvm/lib/IR/Type.cpp        → 类型系统基础
   2. llvm/lib/IR/Value.cpp       → SSA 值模型
   3. llvm/lib/IR/Instruction.cpp → 指令体系
   4. llvm/lib/Transforms/InstCombine/ → 模式匹配优化
   5. llvm/lib/Transforms/Scalar/GVN.cpp → 全局值编号

**路线 B：后端方向**

.. code-block:: text

   1. llvm/lib/Target/X86/        → 目标描述
   2. llvm/lib/CodeGen/SelectionDAG/ → ISel 基础
   3. llvm/lib/CodeGen/MachineScheduler.cpp → 调度
   4. llvm/lib/CodeGen/RegisterAllocator.cpp → 寄存器分配

**路线 C：MLIR 方向**

.. code-block:: text

   1. mlir/include/mlir/IR/        → IR 核心概念
   2. mlir/lib/Dialect/Arith/     → 标准 Dialect 实现
   3. mlir/lib/Conversion/        → Dialect 转换
   4. mlir/lib/Dialect/Linalg/    → 线性代数 Dialect

代码导航技巧
==================

1. **使用 ``git grep``** 快速定位符号：

.. code-block:: console

   $ git grep -n "class Instruction" -- llvm/lib/IR/

2. **使用 ``clang-query``** 分析 AST：

.. code-block:: console

   $ clang-query -c "match functionDecl()" test.cpp

3. **使用 Doxygen 在线文档** （预生成）：

   - LLVM: https://llvm.org/doxygen/
   - MLIR: https://mlir.llvm.org/doxygen/

4. **在 IDE 中设置 include 路径** ：CMake 生成的 ``compile_commands.json``
   可为 IDE（VSCode、Clion）提供完整的代码导航支持。

5. **利用 ``-debug-only`` 输出** 了解 Pass 内部行为：

.. code-block:: console

   $ opt -pass-name -debug-only=pass-name input.ll

LLVM Coding Standards 要点
================================

.. list-table:: LLVM 编码规范快查
   :header-rows: 1

   * - 规则
     - 要求
     - 示例
   * - 命名风格
     - CamelCase 类名，snake_case 变量
     - ``class Instruction``, ``Value *getOperand()``
   * - 头文件
     - 使用 ``#define`` guard
     - ``#define LLVM_IR_INSTRUCTION_H``
   * - 缩进
     - 2 空格，无 Tab
     - ``  int x;``
   * - 注释
     - Doxygen 风格（///）
     - ``/// @brief 描述``
   * - 断言
     - 使用 ``assert()``
     - ``assert(N->getNumUses() > 0)``
   * - Error 处理
     - 使用 ``llvm::Error``
     - ``return llvm::make_error<...>()``
