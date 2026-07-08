.. _chapter-01-03-hello-world:

==========================
Hello World
==========================

前两节我们了解了 LLVM 是什么以及它的架构是怎么设计的。这一节我们动手实践——
从编写 C 代码开始，一步步追踪它经过 LLVM 各阶段最终变成可执行文件的过程。

安装 LLVM/Clang 开发环境
============================

要亲手体验 LLVM 工具链，你需要先安装相关工具。有两种方式：

**方式一：使用系统包管理器（推荐快速上手）**

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt install clang llvm lld

   # macOS (Homebrew)
   brew install llvm

   # 验证安装
   clang --version
   llc --version
   opt --version
   lli --version

**方式二：从源码构建**

如果你希望深入定制 LLVM（比如在自己的架构上做实验，或者调试 LLVM 自身），
可以从源码构建。我们在 ``agents.md`` 中给出了完整的构建步骤，这里简要说明：

.. code-block:: bash

   # 克隆 LLVM 22.x 源码
   git clone --depth 1 --branch llvmorg-22.1.8 \
       https://github.com/llvm/llvm-project.git llvm-project

   cd llvm-project
   cmake -B build -G Ninja \
       -DCMAKE_BUILD_TYPE=RelWithDebInfo \
       -DLLVM_ENABLE_PROJECTS="clang;lld" \
       -DLLVM_TARGETS_TO_BUILD="X86;AArch64;RISCV" \
       -DLLVM_INCLUDE_TESTS=OFF
   ninja -C build

   # 将工具加入 PATH
   export PATH=$PWD/build/bin:$PATH

源码构建的好处是你可以获得完整的调试信息（RelWithDebInfo），并且可以配置
只构建你需要的目标架构（通过 ``LLVM_TARGETS_TO_BUILD``），从而节省编译时间。

从 C 源码到可执行文件
==========================

我们先从一个最熟悉的例子开始。在 ``examples/chapter_01_intro/hello.c`` 中
有一个简单的 C 程序：

.. code-block:: c
   :caption: examples/chapter_01_intro/hello.c

   #include <stdio.h>

   int add(int a, int b) {
       return a + b;
   }

   int main() {
       int x = 42;
       int y = 58;
       int result = add(x, y);
       printf("Result: %d\n", result);
       return 0;
   }

用 Clang 一次编译到底：

.. code-block:: bash

   clang examples/chapter_01_intro/hello.c -o hello
   ./hello
   # 输出: Result: 100

但这样我们就看不到中间过程了。接下来我们用 Clang 的 ``-`` 系列选项来**逐步查看**
LLVM 各阶段的产物。

查看中间产物
===============

**第 1 步：生成 LLVM IR（文本形态）**

.. code-block:: bash

   clang -S -emit-llvm hello.c -o hello.ll

这个命令告诉 Clang：

- ``-S``：只编译到汇编，不汇编
- ``-emit-llvm``：输出 LLVM IR 而不是机器汇编

生成的 ``hello.ll`` 内容如下（简化版）：

.. code-block:: llvm

   ; ModuleID = 'hello.c'
   source_filename = "hello.c"
   target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
   target triple = "x86_64-pc-linux-gnu"

   @.str = private unnamed_addr constant [12 x i8] c"Result: %d\0A\00"

   define i32 @add(i32 %a, i32 %b) {
   entry:
     %add = add nsw i32 %a, %b
     ret i32 %add
   }

   define i32 @main() {
   entry:
     %retval = alloca i32, align 4
     %x = alloca i32, align 4
     %y = alloca i32, align 4
     %result = alloca i32, align 4
     store i32 42, i32* %x, align 4
     store i32 58, i32* %y, align 4
     %0 = load i32, i32* %x, align 4
     %1 = load i32, i32* %y, align 4
     %call = call i32 @add(i32 %0, i32 %1)
     store i32 %call, i32* %result, align 4
     %2 = load i32, i32* %result, align 4
     %call1 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([12 x i8], [12 x i8]* @.str, i64 0, i64 0), i32 %2)
     ret i32 0
   }

   declare i32 @printf(i8*, ...)

注意到几个关键点：

- **``target datalayout``** 描述了目标平台的数据布局（字节序、指针大小、对齐方式等）
- **``target triple``** 指定了目标三元组（CPU-厂商-操作系统）
- 每个函数有明确的 ``define`` 或 ``declare`` 声明
- 全局常量 ``@.str`` 是只读的字符串常量
- **``nsw``** 标记表示 ``add`` 指令不会发生有符号溢出（no signed wrap），帮助优化器做更激进的变换

**第 2 步：生成 LLVM bitcode（二进制形态）**

.. code-block:: bash

   clang -c -emit-llvm hello.c -o hello.bc

``hello.bc`` 是二进制 bitcode 格式，不可读，但更紧凑。可以用 ``llvm-dis``
反汇编回文本格式：

.. code-block:: bash

   llvm-dis hello.bc -o hello.ll     # 从 .bc 反汇编为 .ll
   llvm-as hello.ll -o hello.bc      # 从 .ll 汇编为 .bc

``llvm-dis`` 和 ``llvm-as`` 是 LLVM 的"汇编器/反汇编器"对，就像 GNU 的
``as`` 和 ``objdump`` 一样，但操作对象是 LLVM IR 而非机器码。

**第 3 步：生成目标汇编**

.. code-block:: bash

   clang -S hello.c -o hello.s        # 生成 x86 汇编

这时生成的 ``hello.s`` 就是 x86-64 汇编了，不再是 LLVM IR。

**第 4 步：生成目标文件**

.. code-block:: bash

   clang -c hello.c -o hello.o        # 生成可重定位目标文件

**第 5 步：链接**

.. code-block:: bash

   clang hello.o -o hello             # 链接为可执行文件

这个流程可以用下图总结：

.. mermaid::

   flowchart LR
       S[hello.c] -->|clang -S -emit-llvm| IR[hello.ll]
       S -->|clang -c -emit-llvm| BC[hello.bc]
       IR -->|llvm-as| BC
       BC -->|llvm-dis| IR
       S -->|clang -S| ASM[hello.s]
       S -->|clang -c| OBJ[hello.o]
       OBJ -->|clang ... -o| EXE[hello]
       ASM -->|clang -c| OBJ
       S -->|clang -o| EXE

       style IR fill:#ff9900,stroke:#333,color:#fff
       style BC fill:#ff9900,stroke:#333,color:#fff

使用 opt 运行优化 Pass
==========================

Clang 编译时默认会运行一系列优化 Pass。但如果我们想**单独**运行某个 Pass 来观察
它对 IR 的影响，就需要 ``opt`` 工具。

``opt`` 是 LLVM 的**优化器驱动程序**，它以 LLVM IR 作为输入，应用指定的 Pass 后
输出优化后的 IR。它的源码在 ``llvm/tools/opt/`` 中。

**1. 单 Pass 运行：mem2reg**

我们来看一个具体的例子。先编译到未优化的 IR：

.. code-block:: bash

   # 编译到未优化的 IR（-O0 禁用优化）
   clang -S -emit-llvm -O0 hello.c -o hello.unopt.ll

   # 用 opt 运行 mem2reg Pass（将 alloca/store/load 提升为 SSA 寄存器）
   opt -S -passes=mem2reg hello.unopt.ll -o hello.mem2reg.ll

``-passes=mem2reg`` 告诉 opt 运行 ``mem2reg`` 这个 Pass。运行后，原来的
``alloca``、``store``、``load`` 指令被替换为直接使用 SSA 寄存器：

.. code-block:: llvm

   define i32 @main() {
   entry:
     %call = call i32 @add(i32 42, i32 58)
     %call1 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds (...), i32 %call)
     ret i32 0
   }

看到区别了吗？优化前，``x``、``y``、``result`` 变量都通过 ``alloca`` 分配栈空间
然后 ``store``/``load`` 读写。``mem2reg`` 分析后发现这些变量可以安全地提升为
SSA 值，直接传参给 ``add`` 函数——栈分配和内存读写都被消除了。

**2. 多 Pass 链式运行**

``opt`` 支持在 ``-passes`` 参数中指定多个 Pass, 用逗号分隔, 它们会按顺序依次执行。
例如，先在 ``mem2reg`` 提升 SSA 后，再做 ``instcombine`` （指令合并）和
``simplifycfg`` （简化控制流）：

.. code-block:: bash

   opt -S -passes="mem2reg,instcombine,simplifycfg" hello.unopt.ll -o hello.opt.ll

``instcombine`` 会将冗余的指令模式合并为更简单的形式（比如 ``add x, 0`` → ``x``），
``simplifycfg`` 会合并冗余的基本块、消除不可达代码。三个 Pass 叠加的效果是：
原来十几行的 IR 可能被压缩到只有几行核心逻辑。

**3. 运行完整优化 Pipeline**

如果你想模拟 Clang 的 ``-O2`` 优化行为，可以运行 opt 的默认优化 Pipeline：

.. code-block:: bash

   opt -S -O2 hello.unopt.ll -o hello.O2.ll

这等价于 Clang 的 ``-O2`` 编译选项，会运行数十个 Pass 组成的优化 Pipeline，
包括内联、循环优化、全局优化、指令合并、死代码消除等。查看 ``hello.O2.ll`` 的
内容，你会发现 ``add`` 函数很可能已经被内联到 ``main`` 中了——因为 ``-O2``
启用了函数内联 Pass。

**4. IR 验证**

在运行 Pass 之前，建议先用 ``-verify`` 验证 IR 的合法性：

.. code-block:: bash

   opt -S -passes=verify hello.unopt.ll -o /dev/null

如果 IR 有语法错误或语义问题（如类型不匹配、SSA 违反等），``verify`` Pass 会
输出诊断信息。这个 Pass 在你编写 Pass 或手动修改 IR 时尤其有用。

**5. 查看可用 Pass 列表**

``opt`` 支持超过 100 个 Pass。你可以通过以下命令查看所有可用的 Pass：

.. code-block:: bash

   opt -print-passes

输出会列出所有注册的 Pass 名称，如 ``adce``\ （积极死代码消除）、\ ``gvn``
（全局值编号）、\ ``licm``\ （循环不变式外提）等。

这就是 LLVM Pass 的威力：它可以在不改变程序语义的前提下，对 IR 进行各种变换。
我们会在第 4 章和第 5 章系统学习 Pass 框架和各类优化算法。

使用 lli 直接运行 IR
=======================

LLVM 提供一个 JIT 编译器 ``lli``，可以直接执行 LLVM IR 而不需要经过机器码生成
和链接过程：

.. code-block:: bash

   lli hello.ll
   # 输出: Result: 100

``lli`` 内部做了什么？它在运行时将 IR 编译为当前 CPU 架构的机器码，然后直接
调用执行。这比静态编译少了两步：汇编和链接。对于快速原型验证非常方便。

``lli`` 的源码在 ``llvm/tools/lli/lli.cpp``，它使用 LLVM 的 ORC JIT API
（第 8 章会详细介绍）。

构建一个最小的 LLVM 项目
============================

除了使用命令行工具，你还可以通过 C++ 代码直接调用 LLVM 库来编程式地生成和操作
IR。这是 LLVM 作为"编译器基础设施"的真正价值——你可以把 LLVM 嵌入到自己的
应用程序中。

下面是一个最小化的示例，演示如何用 LLVM C++ API 生成前面 ``add`` 函数的 IR：

.. code-block:: cmake
   :caption: 项目 CMakeLists.txt

   cmake_minimum_required(VERSION 3.20)
   project(MyLLVMProject)

   find_package(LLVM REQUIRED CONFIG)
   message(STATUS "Found LLVM: ${LLVM_DIR}")

   add_executable(my_ir_gen my_ir_gen.cpp)
   target_include_directories(my_ir_gen PRIVATE ${LLVM_INCLUDE_DIRS})
   target_link_libraries(my_ir_gen PRIVATE ${LLVM_LIBS})

.. code-block:: cpp
   :caption: my_ir_gen.cpp

   #include "llvm/IR/LLVMContext.h"
   #include "llvm/IR/Module.h"
   #include "llvm/IR/Function.h"
   #include "llvm/IR/BasicBlock.h"
   #include "llvm/IR/IRBuilder.h"
   #include "llvm/Support/raw_ostream.h"

   using namespace llvm;

   int main() {
       // 创建 LLVM 上下文和模块
       LLVMContext Context;
       auto M = std::make_unique<Module>("my_module", Context);

       // 创建函数签名: i32 (i32, i32)
       FunctionType *FT = FunctionType::get(
           Type::getInt32Ty(Context),      // 返回类型: i32
           {Type::getInt32Ty(Context),     // 参数类型: i32, i32
            Type::getInt32Ty(Context)},
           false);                         // 不是可变参数

       Function *F = Function::Create(
           FT, Function::ExternalLinkage, "add", M.get());

       // 创建基本块并插入指令
       BasicBlock *BB = BasicBlock::Create(Context, "entry", F);
       IRBuilder<> Builder(BB);

       auto Args = F->args().begin();
       Value *A = Args;
       Value *B = Args + 1;
       Value *Result = Builder.CreateAdd(A, B, "result");
       Builder.CreateRet(Result);

       // 打印 IR
       M->print(outs(), nullptr);
       return 0;
   }

构建并运行：

.. code-block:: bash

   mkdir build && cd build
   cmake .. -DLLVM_DIR=/path/to/llvm-project/build/lib/cmake/llvm
   make
   ./my_ir_gen

应该输出我们熟悉的 IR：

.. code-block:: llvm

   ; ModuleID = 'my_module'
   define i32 @add(i32 %0, i32 %1) {
   entry:
     %result = add i32 %0, %1
     ret i32 %result
   }

这个例子展示的是 LLVM 作为库的用法：你不用写任何汇编代码，只用 C++ API 就能
生成经过优化的机器码。这正是 Julia、Rust、Swift 等语言依赖 LLVM 的原因——
它们通过 LLVM 的 C++ API 将各自语言的 IR 翻译到 LLVM IR，然后由 LLVM 处理
后续的优化和代码生成。

**如何找到 LLVM 库？**

上面 CMake 中的 ``find_package(LLVM REQUIRED CONFIG)`` 用于查找 LLVM 的 CMake 配置。
LLVM 构建完成后，会在 ``build/lib/cmake/llvm/`` 目录下生成
``LLVMConfig.cmake`` 。这个文件定义了 ``LLVM_INCLUDE_DIRS`` （头文件路径）和
``LLVM_LIBS`` （需要链接的库列表）。

LLVM 的库采用模块化设计，每个组件对应一个库：

.. code-block:: text

   libLLVMCore.so     # IR 核心（Module, Function, Instruction 等）
   libLLVMAnalysis.so # 分析框架（DominatorTree, LoopInfo 等）
   libLLVMTransformUtils.so # 变换工具
   libLLVMCodeGen.so  # 代码生成器
   libLLVMTarget.so   # 目标描述抽象
   ...

当你链接 ``${LLVM_LIBS}`` 时，CMake 会自动添加所有需要的库。你也可以手动只
链接你需要的库，但通常链接全部是最简单的做法。

.. note::

   从 ``llvm::Module`` 的定义（``llvm/include/llvm/IR/Module.h``）可以看到，
   Module 是一个编译单元的顶层容器，包含 ``GlobalList``（全局变量列表）、
   ``FunctionList``（函数列表）等。当你创建一个 ``Module`` 对象时，你已经在
   构造 LLVM IR 的内存表示——这是所有后续操作（优化、代码生成）的起点。

.. raw:: html

   <hr>
   <p><em>生成日期: 2026-07-08 &nbsp;&nbsp; 项目: 浅入深出 LLVM</em></p>