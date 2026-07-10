.. _chapter-10-03-debugging-llvm:

==========================
LLVM 调试技术
==========================

LLVM 是一个大型的 C++ 项目，它的调试方式与一般 C++ 项目类似，
但也有一些编译器开发特有的工具。

.. rst-class:: center

   调试编译器的特殊之处在于：你调试的是一个 **操作代码的代码**——
   既要处理你自己的 bug，也要处理你生成的代码的 bug。

LLVM_DEBUG 与 -debug
===========================

LLVM 项目中广泛使用 ``LLVM_DEBUG`` 宏来输出调试信息：

.. code-block:: cpp

   #include "llvm/Support/Debug.h"

   void MyPass::run(Function &F) {
       LLVM_DEBUG(dbgs() << "Running MyPass on: " << F.getName() << "\n");

       for (auto &BB : F) {
           LLVM_DEBUG(dbgs() << "  BasicBlock: " << BB.getName() << "\n");
           for (auto &I : BB) {
               LLVM_DEBUG(dbgs() << "    " << I << "\n");
           }
       }
   }

**关键点** ： ``LLVM_DEBUG`` 在 Release 模式 **不产生任何代码** 。只有 Debug 构建
或 Release 构建时用 ``-DLLVM_ENABLE_ASSERTIONS=ON`` 才会编译进去。

运行时通过 ``-debug`` 或 ``-debug-only`` 控制输出：

.. code-block:: console

   # 输出所有调试信息
   $ opt -debug -passes='my-pass' input.ll

   # 只输出特定模块的调试信息
   $ opt -debug-only=my-pass input.ll

   # 多个模块
   $ opt -debug-only=my-pass,licm input.ll

``-debug-only`` 的参数对应 ``LLVM_DEBUG`` 宏中的 ``dbgs()`` 的 DEBUG_TYPE 标签：

.. code-block:: cpp

   #define DEBUG_TYPE "my-pass"
   LLVM_DEBUG(dbgs() << "This only shows with -debug-only=my-pass\n");
   #undef DEBUG_TYPE

STATISTIC 与统计信息收集
==============================

``STATISTIC`` 宏定义可在多个 Pass 间累加的计数器：

.. code-block:: cpp

   #include "llvm/ADT/Statistic.h"

   #define DEBUG_TYPE "my-pass"
   STATISTIC(NumDeleted, "Number of instructions deleted");
   STATISTIC(NumSimplified, "Number of instructions simplified");
   #undef DEBUG_TYPE

   PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM) {
       for (auto &I : ...) {
           if (shouldDelete(I)) {
               NumDeleted++;  // 统计计数
           }
       }
   }

用 ``-stats`` 查看：

.. code-block:: console

   $ opt -passes='my-pass' -stats input.ll
   5 my-pass - Number of instructions deleted
   2 my-pass - Number of instructions simplified

``STATISTIC`` 在 Release 模式下也会被编译进去，但默认不显示（需要 ``-stats`` ）。

MachineVerifier 与 IR Verifier
======================================

LLVM 自带两个"自动检查员"：

**IR Verifier** ：验证 LLVM IR 的一致性。

.. code-block:: console

   $ opt -verify input.ll   # 验证 IR
   # 如果 IR 有问题，输出错误信息

自动在 ``opt`` 和 ``llc`` 的默认管道中运行。如果要禁用：

.. code-block:: console

   $ opt -disable-verify ...

**MachineVerifier** ：验证 MachineInstr 的一致性（后端）。

.. code-block:: console

   $ llc -verify-machineinstrs input.ll

MachineVerifier 检查：

- 指令操作数类型是否正确
- 寄存器约束是否满足
- 虚拟寄存器是否在分配前被使用
- 基本块是否以终止指令结尾

在 Pass 开发过程中，建议始终开启 ``-verify`` 。

opt 的调试工具
====================

.. code-block:: console

   # 在每个 Pass 之后打印 IR
   $ opt -passes='mem2reg,gvn' -print-after-all input.ll

   # 只显示发生变化的 IR
   $ opt -passes='mem2reg,gvn' -print-changed input.ll

   # 显示 Pass 的执行顺序
   $ opt -passes='default<O2>' -print-pipeline-passes

   # 带颜色的 diff（需要终端支持）
   $ opt -passes='mem2reg' -print-after-all -color input.ll

GDB 调试 LLVM 的最佳实践
===============================

**1. Debug 构建 LLVM**

.. code-block:: console

   $ cmake -B build -DCMAKE_BUILD_TYPE=Debug -DLLVM_ENABLE_ASSERTIONS=ON ...
   $ ninja -C build

**2. 在优化 Pass 中设置断点**

.. code-block:: console

   $ gdb --args opt -passes='my-pass' input.ll -S -o output.ll
   (gdb) b MyPass::run
   (gdb) r

**3. 使用 LLVM 的 Pretty Print**

.. code-block:: cpp

   // 在 GDB 中打印 IR 对象
   (gdb) p F         // 打印 Function
   (gdb) p I         // 打印 Instruction
   (gdb) p *M       // 打印 Module

**4. 使用 LLVM_GLOBALVIS_SET 快速定位**

让 LLVM 在遇到特定值时进入 debugger：

.. code-block:: console

   $ opt -passes='my-pass' -debug -fatal-llvm-if-error ...

断点调试技巧：

.. code-block:: text

   # 在 LLVM 的公共函数上设置条件断点
   (gdb) b llvm::Function::dump()
   (gdb) condition 1 F.getName() == "myFunc"

bugpoint：最小化测试用例
==============================

``bugpoint`` 是 LLVM 的 **自动化测试用例最小化工具** 。当发现一个 Pass 有 bug 时，
用 bugpoint 可以将触发 bug 的大型 IR 文件缩小到最小可复现版本：

.. code-block:: console

   # 找到导致崩溃的最小 IR
   $ bugpoint -opt-command=opt input.bc -run-opt
   # bugpoint 输出：/tmp/bugpoint-reduced-simplified.bc

   # 找到导致错误输出的 Pass
   $ bugpoint input.bc -run-opt -opt-func=MyPass

llvm-reduce：更现代的缩减工具
======================================

``llvm-reduce`` 是 ``bugpoint`` 的现代替代品，它通过自动删除 IR 中的非必要部分
来最小化测试用例：

.. code-block:: console

   $ llvm-reduce --test=test_script.sh input.ll -o reduced.ll
   # test_script.sh 是一个返回 0（成功）或 1（失败）的脚本
   # llvm-reduce 自动从 input.ll 中删除内容，
   # 只要 test_script.sh 仍然返回 1（复现 bug），就继续删除

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
