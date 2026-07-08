.. _chapter-02-03-module-function-basicblock:

========================================
Module、Function、BasicBlock 结构
========================================

前面两节我们从语法层面认识了 IR 的指令和类型。这一节我们从**结构** 的角度来看
LLVM IR 在内存中的层次组织。

Module -- 编译单元的顶层容器
================================

``Module`` 是 LLVM IR 的顶层容器（``llvm/include/llvm/IR/Module.h`` ）：

.. code-block:: cpp
   :caption: llvm/include/llvm/IR/Module.h（节选）

   class Module {
     LLVMContext &Context;
     GlobalListType GlobalList;          // 全局变量列表
     FunctionListType FunctionList;      // 函数列表
     NamedMDListType NamedMDList;        // 命名元数据列表
     std::string SourceFileName;
     DataLayout DL;
     Triple TargetTriple;
   };

一个 ``Module`` 实例对应一个编译单元，包含全局变量、函数、命名元数据、
目标描述等信息。

**关键操作：**

.. code-block:: cpp

   // 遍历所有函数
   for (auto &F : *M) { /* F 是 Function */ }

   // 遍历所有全局变量
   for (auto &GV : M->globals()) { /* GV 是 GlobalVariable */ }

   // 按名称查找函数
   Function *F = M->getFunction("main");

   // 获取或插入函数声明
   FunctionCallee F = M->getOrInsertFunction("printf",
       FunctionType::get(IntegerType::getInt32Ty(Context),
           {PointerType::getUnqual(Context)}, true));

Function -- 可执行代码的单元
================================

``Function`` 表示一个函数，包含参数列表、基本块列表和属性。

**创建函数：**

.. code-block:: cpp

   FunctionType *FT = FunctionType::get(
       Type::getInt32Ty(Context),       // 返回类型
       {Type::getInt32Ty(Context),
        Type::getInt32Ty(Context)},     // 参数类型
       false);
   Function *F = Function::Create(
       FT, Function::ExternalLinkage, "add", M.get());

**链接类型：**

.. list-table::
   :header-rows: 1

   * - 链接类型
     - 含义
   * - ``ExternalLinkage``
     - 外部可见（普通函数）
   * - ``InternalLinkage``
     - 仅当前模块可见（``static`` ）
   * - ``WeakAnyLinkage``
     - 弱符号（``__attribute__((weak))`` ）

**函数体遍历：**

.. code-block:: cpp

   for (auto &BB : *F) { /* 遍历基本块 */ }
   for (auto &Arg : F->args()) { /* 遍历参数 */ }
   F->hasFnAttribute(Attribute::NoInline);

BasicBlock -- 顺序执行的基本单元
====================================

``BasicBlock`` 内的指令**顺序执行** ，以**终止指令** 结尾。

.. code-block:: llvm

   entry:
     %a = add i32 %x, 1
     %b = mul i32 %a, 2
     br label %next   ; 终止指令

**核心规则：** 每个基本块有且仅有一条终止指令；基本块内的指令顺序执行。

**前驱和后继：**

.. code-block:: cpp

   for (BasicBlock *Pred : predecessors(&BB)) { /* ... */ }
   for (BasicBlock *Succ : successors(&BB)) { /* ... */ }

**基本块操作：**

.. code-block:: cpp

   BasicBlock *BB = BasicBlock::Create(Context, "entry", F);
   IRBuilder<> Builder(BB);
   Value *V = Builder.CreateAdd(A, B, "result");
   BasicBlock *NewBB = BB->splitBasicBlock(SomeInst, "new_label");

Instruction -- 指令
=======================

``Instruction`` 是 IR 中最细粒度的单位，每个指令有**操作码** 和**操作数列表** 。

**操作码枚举：** 定义在 ``llvm/include/llvm/IR/Instruction.def`` 中，
包括 ``Instruction::Add`` 、\ ``Instruction::Load`` 、\ ``Instruction::Br`` 等
约 100+ 个操作码。

**操作数操作：**

.. code-block:: cpp

   Value *Op0 = I->getOperand(0);
   unsigned NumOps = I->getNumOperands();
   I->replaceAllUsesWith(NewValue);

**双向 def-use 链：**

.. code-block:: cpp

   // 从值到使用者
   for (User *U : V->users()) { /* U 是使用 V 的指令 */ }

   // 从指令到值
   for (Use &U : I->operands()) {
     Value *V = U.get();  // V 是 I 的操作数
   }

Value -- 一切值的基类
=========================

``Value`` 是所有 IR 可引用对象的基类，定义在 ``llvm/include/llvm/IR/Value.h`` 中：

.. code-block:: cpp

   class Value {
     Type *VTy;           // 值的类型
     Use *UseList;        // 使用此值的所有 Use 节点链表
     unsigned SubclassID; // 子类标识
   };

**继承层次：**

.. code-block:: text

   Value
     +-- Constant        # 编译时常量
     |     +-- ConstantInt / ConstantFP / GlobalValue / UndefValue
     +-- Argument        # 函数参数
     +-- BasicBlock      # 基本块引用
     +-- Instruction     # 所有指令的基类

**replaceAllUsesWith -- 最强大的方法：**

.. code-block:: cpp

   old->replaceAllUsesWith(new);  // 将所有使用 %old 的地方替换为 %new

这个操作遍历所有使用 ``%old`` 的指令，将操作数替换为 ``%new`` 。
如果 ``%old`` 不再被使用，它就可以被安全删除。实现位于 ``llvm/lib/IR/Value.cpp`` 。