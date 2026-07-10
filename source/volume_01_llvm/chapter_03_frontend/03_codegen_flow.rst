.. _chapter-03-03-codegen-flow:

==========================
代码生成流程
==========================

从 AST 到 LLVM IR 的转换是 Clang 前端最后的、也是最关键的一步——**代码生成**
（CodeGen）。这一步之后，你的 C/C++ 代码就变成了第 2 章中我们看到的 LLVM IR。

.. rst-class:: center

   AST 是"树状的语法表示"，而 LLVM IR 是"线性的指令序列"。
   代码生成要做的，就是把树"拍平"成指令流。

从整体上看，代码生成的流水线是这样的：

.. mermaid::

   flowchart LR
       A[AST] --> B[CodeGen 入口]
       B --> C[CodeGenFunction / CodeGenModule]
       C --> D[表达式生成]
       C --> E[语句生成]
       C --> F[函数生成]
       D --> G[LLVM IR]
       E --> G
       F --> G

       style A fill:#4a9eff,color:#fff
       style G fill:#ff9800,color:#fff

CodeGenFunction 与 CodeGenModule
====================================

Clang 的代码生成器位于 ``clang/lib/CodeGen/`` 目录下。两个核心类是：

- **CodeGenModule** （CGM）：代表整个翻译单元的代码生成上下文
- **CodeGenFunction** （CGF）：代表单个函数的代码生成上下文

``CodeGenModule`` 的职责包括：

.. code-block:: cpp
   :caption: clang/lib/CodeGen/CodeGenModule.h

   class CodeGenModule {
       ASTContext &Context;          // AST 上下文
       llvm::Module &TheModule;     // 目标 LLVM Module
       llvm::LLVMContext &VMContext; // LLVM 上下文
       // ... 类型转换、全局变量、构造函数等
   };

``CodeGenFunction`` 的职责更聚焦——它负责为一个 ``FunctionDecl`` 生成 ``llvm::Function`` ：

.. code-block:: cpp
   :caption: clang/lib/CodeGen/CodeGenFunction.h

   class CodeGenFunction {
       CodeGenModule &CGM;
       llvm::Function *CurFn;       // 当前正在生成的 LLVM 函数
       llvm::LLVMBuilderBase *Builder; // IRBuilder，用于创建 IR 指令
       // ... 局部变量分配、控制流结构等
   };

简单来说： **CGM 管"全局"，CGF 管"当前函数"** 。

表达式生成
=========================

表达式生成是最核心的部分之一，因为它涉及递归地将 AST 表达式子树
转换为 LLVM IR 指令。

假设我们有表达式 ``a + b`` ：

.. mermaid::

   flowchart TD
       A["BinaryOperator '+'] --> B[访问左子表达式 'a']
       A --> C[访问右子表达式 'b']
       B --> D["生成 DeclRefExpr → load %a"]
       C --> E["生成 DeclRefExpr → load %b"]
       D --> F["Builder.CreateAdd(val_a, val_b)"]
       E --> F
       F --> G["生成 llvm::Value* = add i32 %a, %b"]

       style A fill:#e91e63,color:#fff
       style G fill:#ff9800,color:#fff

Clang 的表达式生成分为两个主要 emitter：

- **ScalarExprEmitter** ：生成标量值（整数、浮点数、指针等）
- **AggExprEmitter** ：生成聚合值（结构体、数组等）

以最简单的 ``IntegerLiteral`` 为例：

.. code-block:: cpp
   :caption: clang/lib/CodeGen/CGExprScalar.cpp

   Value *ScalarExprEmitter::VisitIntegerLiteral(const IntegerLiteral *E) {
       // 直接创建一个 LLVM 常量
       return llvm::ConstantInt::get(ConvertType(E->getType()), E->getValue());
   }

而对于 ``BinaryOperator`` ：

.. code-block:: cpp
   :caption: clang/lib/CodeGen/CGExprScalar.cpp（简化）

   Value *ScalarExprEmitter::VisitBinaryOperator(const BinaryOperator *E) {
       // 先递归生成左右操作数
       Value *LHS = Visit(E->getLHS());
       Value *RHS = Visit(E->getRHS());

       // 根据操作符类型生成不同的 LLVM 指令
       switch (E->getOpcode()) {
       case BO_Add:
           return Builder.CreateAdd(LHS, RHS, "addtmp");
       case BO_Sub:
           return Builder.CreateSub(LHS, RHS, "subtmp");
       // ...
       }
   }

注意这里 **递归下降** 的模式——``VisitBinaryOperator`` 先递归调用 ``Visit`` 处理
左右子表达式，然后根据操作符类型创建不同的 LLVM 指令。这个模式贯穿了整个代码生成器。

语句生成
=========================

语句生成比表达式简单一些，因为语句通常不产生值，只产生"副作用"（控制流、内存写入等）。

以 ``return`` 语句为例：

.. code-block:: cpp
   :caption: clang/lib/CodeGen/CGStmt.cpp（简化）

   void CodeGenFunction::EmitReturnStmt(const ReturnStmt *S) {
       if (const Expr *RetVal = S->getRetValue()) {
           // 生成返回值表达式 → 得到 llvm::Value
           llvm::Value *V = EmitScalarExpr(RetVal);
           // 创建 ret 指令
           Builder.CreateRet(V);
       } else {
           Builder.CreateRetVoid();
       }
   }

控制流语句（ ``if`` 、 ``for`` 、 ``while`` ）会创建 LLVM 的 basic block 和分支指令：

.. code-block:: cpp
   :caption: clang/lib/CodeGen/CGStmt.cpp（简化）

   void CodeGenFunction::EmitIfStmt(const IfStmt *S) {
       // 创建三个 basic block
       llvm::BasicBlock *ThenBlock = createBasicBlock("if.then");
       llvm::BasicBlock *ElseBlock = createBasicBlock("if.else");
       llvm::BasicBlock *ContBlock = createBasicBlock("if.end");

       // 生成条件表达式
       llvm::Value *Cond = EmitScalarExpr(S->getCond());
       // 创建条件分支
       Builder.CreateCondBr(Cond, ThenBlock, ElseBlock);

       // 生成 then 分支
       EmitBlock(ThenBlock);
       EmitStmt(S->getThen());
       Builder.CreateBr(ContBlock);

       // 生成 else 分支
       EmitBlock(ElseBlock);
       EmitStmt(S->getElse());
       Builder.CreateBr(ContBlock);

       // 继续在 merge 点生成代码
       EmitBlock(ContBlock);
   }

这正是第 2 章中我们看到的 ``br i1 %cond, label %if.then, label %if.else``
这类条件分支指令的来源。

函数生成
=========================

一个完整的函数生成流程包括：

1. **创建函数签名** ：根据 ``FunctionDecl`` 的信息（返回类型、参数类型）创建 ``llvm::FunctionType``
2. **创建 LLVM Function** ：在 ``llvm::Module`` 中创建 ``llvm::Function``
3. **创建入口基本块** ：为函数体创建第一个 basic block
4. **处理参数** ：将 LLVM 函数的参数与 AST 中的 ``ParmVarDecl`` 关联
5. **生成函数体** ：用 ``CodeGenFunction`` 遍历函数体内的语句
6. **设置调用约定和属性** ：设置 ``nobuiltin`` 、 ``optnone`` 、 ``inline`` 等属性

ABI 处理
=========================

这是一块比较复杂的内容。不同平台、不同语言有不同的调用约定（Calling Convention）。
Clang 的 CodeGen 需要一个中间层来处理 ABI 相关的转换。

**x86_64 参数传递规则示例：**

.. code-block:: text

   // C 函数
   struct Point { double x; double y; };
   double distance(struct Point p);

   // 在 x86_64 System V ABI 下，struct Point 会被拆分为两个 double
   // 分别通过 %xmm0 和 %xmm1 传递：
   //   define double @distance(double %p.coerce0, double %p.coerce1)

而如果结构体更大，则可能通过内存传递：

.. code-block:: text

   struct Big { int arr[8]; };
   void process(struct Big b);

   // 在 x86_64 下，超过 4 个 8 字节的结构体通过内存传递：
   //   define void @process(ptr %b)

Clang 中 ABI 处理的代码位于 ``clang/lib/CodeGen/TargetInfo.cpp`` ，不同架构
有不同的 ``ABIInfo`` 实现：

- ``X86_64ABIInfo``
- ``AArch64ABIInfo``
- ``RISCVABIInfo``
- 等等

每个 ``ABIInfo`` 负责描述"这种架构下如何把 C 类型映射到 LLVM 类型"。

Itanium C++ ABI
=====================================

对于 C++，Clang 默认使用 **Itanium C++ ABI** （即使在非 Itanium 架构上）。
这个 ABI 定义了：

- 名称修饰（Name Mangling）： ``int foo(int)`` → ``_Z3fooi``
- 虚函数表（vtable）的布局
- RTTI（Run-Time Type Information）的表示
- 异常处理（Itanium C++ Exception Handling）
- 构造函数和析构函数的调用顺序

名称修饰是 C++ 编译中最常见的"魔法"之一。你可以在 ``clang`` 中看到修饰后的名称：

.. code-block:: console

   $ echo "int foo(int x) { return x; }" | clang -cc1 -emit-llvm -o - -x c++
   ...
   define i32 @_Z3fooi(i32 %x) {
       ret i32 %x
   }

``_Z3fooi`` 中的 ``_Z`` 是 Itanium ABI 的前缀， ``3foo`` 是函数名（3 是名字长度），
``i`` 是参数类型（int）。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
