.. _chapter-04-05-transform-passes:

==========================
变换 Pass 详解
==========================

分析 Pass 告诉我们 IR 的"信息"，而变换 Pass 真正去做"修改"。本节我们编写一个
有实际意义的变换 Pass，走完从设计到测试的全流程。

.. rst-class:: center

   一个变换 Pass 的完整生命周期：分析 → 修改 → 声明保留 → 固化到管道。

实战目标：恒等传播 Pass
============================

我们的目标是编写一个简单的优化 Pass，它做一件事：

.. code-block:: text

   把这样的代码：
     %add = add i32 %a, 0
     %mul = mul i32 %b, 1

   优化为：
     ; %add 直接替换为 %a
     ; %mul 直接替换为 %b

这叫做"恒等传播"（Identity Propagation）——消除无效的算术运算。
虽然 ``instcombine`` 已经做了这件事，但作为教学示例，它足够简单且有意义。

第一步：编写 Pass 框架
============================

.. code-block:: cpp

   // IdentityPropagation.cpp
   #include "llvm/IR/PassManager.h"
   #include "llvm/IR/Function.h"
   #include "llvm/IR/Instruction.h"
   #include "llvm/IR/IRBuilder.h"
   #include "llvm/Support/raw_ostream.h"
   using namespace llvm;

   struct IdentityPropagationPass
       : public PassInfoMixin<IdentityPropagationPass> {

       PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM) {
           return PreservedAnalyses::all();  // 先占位
       }
   };

第二步：实现核心逻辑
============================

我们遍历函数中的每一条指令，检查恒等模式：

.. code-block:: cpp

   PreservedAnalyses run(Function &F, FunctionAnalysisManager &AM) {
       bool Changed = false;

       for (BasicBlock &BB : F) {
           for (Instruction &I : BB) {
               // 检查 add/sub 恒等模式：x + 0, x - 0
               if (auto *BO = dyn_cast<BinaryOperator>(&I)) {
                   Value *LHS = BO->getOperand(0);
                   Value *RHS = BO->getOperand(1);

                   switch (BO->getOpcode()) {
                   case Instruction::Add:
                   case Instruction::Sub:
                       if (isa<ConstantInt>(RHS) &&
                           cast<ConstantInt>(RHS)->isZero()) {
                           // x + 0 → x,  x - 0 → x
                           I.replaceAllUsesWith(LHS);
                           Changed = true;
                       }
                       break;

                   case Instruction::Mul:
                       if (isa<ConstantInt>(RHS) &&
                           cast<ConstantInt>(RHS)->isOne()) {
                           // x * 1 → x
                           I.replaceAllUsesWith(LHS);
                           Changed = true;
                       }
                       break;

                   case Instruction::SDiv:
                   case Instruction::UDiv:
                       if (isa<ConstantInt>(RHS) &&
                           cast<ConstantInt>(RHS)->isOne()) {
                           // x / 1 → x
                           I.replaceAllUsesWith(LHS);
                           Changed = true;
                       }
                       break;

                   default:
                       break;
                   }
               }
           }
       }

       // 如果 IR 被修改，声明某些分析已失效
       if (Changed) {
           auto PA = PreservedAnalyses::none();
           // 实际上我们的改动很小，可以精确声明哪些仍有效
           return PA;
       }
       return PreservedAnalyses::all();
   }

第三步：添加 IRBuilder 使用
=============================

有时我们需要的变换不只是"替换"指令，而是"插入"新指令。此时用到 ``IRBuilder`` 。

假设我们要实现一个更复杂的变换：**将 ``a * 2`` 替换为 ``a + a``** （加法通常比乘法快）：

.. code-block:: cpp

   if (BO->getOpcode() == Instruction::Mul) {
       if (auto *C = dyn_cast<ConstantInt>(RHS)) {
           if (C->getValue() == 2) {
               // 在当前位置创建加法指令
               IRBuilder<> Builder(&I);
               Value *NewAdd = Builder.CreateAdd(LHS, LHS, "double");
               I.replaceAllUsesWith(NewAdd);
               Changed = true;
           }
       }
   }

``IRBuilder`` 的构造函数接受一个指令指针，表示"在这个指令之前插入"。
创建指令时不需要手动管理 ``Value`` 的生命周期——IRBuilder 自动处理。

第四步：注册 Pass
============================

将 Pass 注册到插件系统：

.. code-block:: cpp

   extern "C" LLVM_ATTRIBUTE_WEAK PassPluginLibraryInfo
   llvmGetPassPluginInfo() {
       return {
           LLVM_PLUGIN_API_VERSION,
           "IdentityPropagation",
           "v0.1",
           [](PassBuilder &PB) {
               PB.registerPipelineParsingCallback(
                   [](StringRef Name, FunctionPassManager &FPM,
                      ArrayRef<PassBuilder::PipelineElement>) {
                       if (Name == "identity-prop") {
                           FPM.addPass(IdentityPropagationPass());
                           return true;
                       }
                       return false;
                   });
           }};
   }

编译和运行：

.. code-block:: console

   $ clang++ -shared -fPIC -o libIdentityProp.so \
       IdentityPropagation.cpp \
       `llvm-config --cxxflags --ldflags --libs`

   $ opt -load-pass-plugin=./libIdentityProp.so \
         -passes='identity-prop' input.ll -S -o output.ll

测试与验证：使用 FileCheck
============================

LLVM 社区推荐使用 ``FileCheck`` 工具来测试 Pass 的正确性：

.. code-block:: llvm
   :caption: test/identity-prop.ll

   ; RUN: opt -load-pass-plugin=%libdir/libIdentityProp.so \
   ; RUN:     -passes='identity-prop' -S %s | FileCheck %s

   define i32 @test(i32 %a, i32 %b) {
   ; CHECK-LABEL: @test
   ; CHECK:         %b
   ; CHECK-NEXT:    ret i32 %b

       %1 = add i32 %b, 0    ; 应该被替换为 %b
       %2 = mul i32 %a, 1    ; 应该被替换为 %a
       %3 = add i32 %1, %2   ; 现在实际是 %b + %a
       ret i32 %3
   }

运行测试：

.. code-block:: console

   $ llvm-lit test/identity-prop.ll

如果在 LLVM 源码树外运行：

.. code-block:: console

   $ opt -load-pass-plugin=./libIdentityProp.so \
         -passes='identity-prop' -S test/identity-prop.ll | FileCheck test/identity-prop.ll

常见的 IR 修改操作
======================

.. list-table:: IRBuilder 常用操作
   :header-rows: 1

   * - 操作
     - API
     - 说明
   * - 创建加法
     - ``Builder.CreateAdd(LHS, RHS, "name")``
     - 整数或浮点加法
   * - 创建函数调用
     - ``Builder.CreateCall(Callee, Args)``
     - 调用 IR 中的函数
   * - 创建 load
     - ``Builder.CreateLoad(Ptr)``
     - 从指针读取值
   * - 创建 store
     - ``Builder.CreateStore(Val, Ptr)``
     - 写入指针指向的内存
   * - 创建分支
     - ``Builder.CreateCondBr(Cond, TrueBB, FalseBB)``
     - 条件分支
   * - 创建 alloca
     - ``Builder.CreateAlloca(Type, Count, "name")``
     - 栈上分配
   * - 获取当前插入点
     - ``Builder.GetInsertPoint()``
     - 返回当前插入位置的迭代器
   * - 设置插入点
     - ``Builder.SetInsertPoint(BB, It)``
     - 改变插入位置

删除指令的注意事项
=====================

删除指令时需要小心——被删除的指令必须没有任何使用者（use）：

.. code-block:: cpp

   // 错误做法：直接删除还有使用者的指令
   I.eraseFromParent();  // 崩溃！I 的结果还在其他地方被使用

   // 正确做法：
   // 1. 先用 replaceAllUsesWith 替换所有使用
   I.replaceAllUsesWith(NewVal);
   // 2. 确认没有使用后删除
   if (I.use_empty()) {
       I.eraseFromParent();
   }

更简洁的方式是用 ``RecursivelyDeleteTriviallyDeadInstructions`` ：

.. code-block:: cpp

   #include "llvm/Transforms/Utils/Local.h"
   // 自动删除死指令（递归删除没有使用的指令链）
   RecursivelyDeleteTriviallyDeadInstructions(&I);

运行 Pass 后的调试方法
============================

.. code-block:: console

   # 查看 Pass 管道的执行过程
   $ opt -passes='identity-prop' -print-after-all input.ll

   # 只打印特定函数的变化
   $ opt -passes='identity-prop' \
         -filter-print-funcs='myFunction' input.ll

   # 统计信息（需要在 Pass 中注册 STATISTIC）
   $ opt -passes='identity-prop' -stats input.ll

.. rubric:: 进一步阅读

- `Writing an LLVM New PM Pass <https://llvm.org/docs/WritingAnLLVMNewPMPass.html>`_ — New PM Pass 编写指南
- `LLVM Pass 文档 <https://llvm.org/docs/Passes.html>`_ — 所有内置 Pass 的参考
- Chandler Carruth 的 LLVM Developers Meeting 演讲：*The New Pass Manager* (2017)


--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
