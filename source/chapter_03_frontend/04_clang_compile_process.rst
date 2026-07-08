.. _chapter-03-04-clang-compile-process:

==========================
Clang 编译过程详解
==========================

前三节我们分别看了 Clang 的总体设计、AST 结构和代码生成流程。现在把它们串起来，
走一遍从源码到 LLVM IR 的**完整流水线**。

.. rst-class:: center

   编译器的每一阶段都在做同一件事：**把信息从一种形式转换为另一种形式，
   每一步保留语义、降低抽象层次**。

.. mermaid::

   flowchart TD
       A[源码 \n .c / .cpp] --> B[预处理 Preprocessor]
       B --> C[预处理后的源码]
       C --> D[词法分析 Lexer]
       D --> E[Token 流]
       E --> F[语法分析 Parser]
       F --> G[AST]
       G --> H[语义分析 Sema]
       H --> I[带类型信息的 AST]
       I --> J[代码生成 CodeGen]
       J --> K[LLVM IR \n .ll / .bc]

       style A fill:#4caf50,color:#fff
       style K fill:#ff9800,color:#fff

预处理（Preprocessing）
============================

预处理是编译的第一阶段，但它实际上**不属于 Clang 的"编译"部分**——它只是一个
文本处理阶段，处理以 ``#`` 开头的预处理器指令。

.. code-block:: console

   # 单独运行预处理
   $ clang -E hello.c -o hello.i

预处理主要做这几件事：

1. **头文件展开**：将 ``#include`` 替换为对应头文件的内容
2. **宏展开**：将 ``#define`` 定义的宏替换为展开后的代码
3. **条件编译**：处理 ``#if`` / ``#ifdef`` / ``#endif`` 等指令
4. **行号标记**：插入 ``#line`` 指令，告诉编译器后面的代码来自哪个文件和行号
5. **删除注释**：将 ``/* ... */`` 和 ``//`` 注释替换为空格

预处理的结果是一个**纯文本文件**，不再包含任何预处理器指令。你可以用 ``-E``
选项查看预处理后的结果，这对调试宏非常有用：

.. code-block:: console

   $ cat test.c
   #define MAX(a, b) ((a) > (b) ? (a) : (b))
   int main() { return MAX(1, 2); }

   $ clang -E test.c
   # 1 "test.c"
   # 1 "<built-in>"
   int main() { return ((1) > (2) ? (1) : (2)); }

注意 ``MAX(1, 2)`` 被展开成了 ``((1) > (2) ? (1) : (2))``。

词法分析（Lexing）
========================

预处理完成后，Clang 的 **Lexer** （词法分析器）开始工作。它的输入是预处理后的
源码文本，输出是一串 **Token** （记号）。

.. code-block:: c

   // 源码：
   int result = a + 42;

Lexer 会依次输出以下 Token：

.. code-block:: text

   Token 1: 关键字 'int'
   Token 2: 标识符 'result'
   Token 3: 标点符号 '='
   Token 4: 标识符 'a'
   Token 5: 标点符号 '+'
   Token 6: 整数字面量 '42'
   Token 7: 标点符号 ';'

每个 Token 记录了三类信息：

- **类型** （TokenKind）：关键字、标识符、字面量、标点符号等
- **内容** （ IdentifierInfo 或 LiteralData）：具体的文本或值
- **位置** （SourceLocation）：在源码中的位置（文件、行、列）

Clang 的 Lexer 实现位于 ``clang/lib/Lex/``，核心类是 ``clang::Lexer``。

语法分析（Parsing）
=========================

Parser（语法分析器）从 Lexer 获取 Token 流，根据语言的语法规则，
将其组织成**抽象语法树（AST）**。

.. code-block:: text

   Token 流:  int  result  =  a  +  42  ;
                 ↓       ↓     ↓  ↓   ↓   ↓
   Parser:   ────────────────────────────────→  AST

Parser 的核心是**递归下降解析**——每个语法结构对应一个解析函数：

.. code-block:: cpp
   :caption: clang/lib/Parse/Parser.cpp（示意）

   Parser::DeclGroupPtrTy Parser::ParseDeclaration() {
       if (Tok.is(tok::kw_int)) {
           return ParseSimpleDeclaration();  // 处理 int x = ...;
       }
       if (Tok.is(tok::kw_struct)) {
           return ParseStructDeclaration();  // 处理 struct ...;
       }
       // ... 其他情况
   }

例如，当遇到 ``int x = 42;`` 时，解析过程大致是：

1. ``ParseDeclaration`` 看到 ``int`` → 调用 ``ParseSimpleDeclaration``
2. ``ParseDeclarator`` 解析 ``x`` → 得到声明符（declarator）
3. ``ParseInitializer`` 看到 ``=`` → 调用 ``ParseAssignmentExpression``
4. ``ParseAssignmentExpression`` 解析 ``42`` → 创建 ``IntegerLiteral`` 节点
5. 将 ``VarDecl`` 节点挂到 ``TranslationUnitDecl`` 下

Clang 的 Parser 实现位于 ``clang/lib/Parse/``，核心类是 ``clang::Parser``。

语义分析（Sema）
=========================

AST 建好了，但此时它只反映了**代码长什么样**，还不清楚**代码含义是否正确**。
语义分析（Semantic Analysis）负责：

1. **类型检查**：确保操作数类型与操作符匹配
2. **名字查找**：找到每个名字对应的声明（变量、函数、类型等）
3. **重载决议**：在多个同名的函数中选出最匹配的一个
4. **隐式转换插入**：在需要的地方插入 ``ImplicitCastExpr``、``ImplicitConversionSequence``
5. **模板实例化**：在需要时触发模板的实例化

以 ``int x = 3.14;`` 为例——Sema 会发现右侧是 ``double`` 而左侧是 ``int``，
在 AST 中插入一个 ``ImplicitCastExpr``：

.. code-block:: text

   VarDecl 'int x'
   └── ImplicitCastExpr <FloatingToIntegral>  ← Sema 插入的
       └── FloatingLiteral '3.14'

Sema 的实现在 ``clang/lib/Sema/``，这是一个非常庞大的模块。每个 Sema 函数
处理一种语法结构的语义检查：

.. code-block:: cpp
   :caption: clang/lib/Sema/SemaExpr.cpp（示意）

   ExprResult Sema::ActOnBinOp(SourceLocation OpLoc, tok::TokenKind Opc,
                                Expr *LHS, Expr *RHS) {
       // 1. 检查左右操作数类型是否兼容
       QualType LHSType = LHS->getType();
       QualType RHSType = RHS->getType();

       // 2. 检查操作符是否可用（比如指针不能做乘法）
       if (!isValidForBinOp(Opc, LHSType, RHSType)) {
           Diag(OpLoc, diag::err_typecheck_invalid_operands)
               << LHSType << RHSType << LHS->getSourceRange();
           return ExprError();
       }

       // 3. 隐式类型转换
       ExprResult LHSConv = PerformImplicitConversion(LHS, ExpectedType);

       // 4. 创建 AST 节点
       return new (Context) BinaryOperator(LHSConv.get(), RHS, Opc, ResultType);
   }

IR 生成（CodeGen）
=========================

经过语义分析后，AST 已经完整且正确。最后一步是 **CodeGen** ——将带类型信息的
AST 转换为 LLVM IR。

.. code-block:: console

   # 从 C 源码直接生成 LLVM IR
   $ clang -S -emit-llvm hello.c -o hello.ll

   # 查看各阶段的时间分布
   $ clang -ccc-print-phases hello.c

CodeGen 的入口是 ``CodeGenModule::EmitTopLevelDecl()``，它会遍历 ``TranslationUnitDecl``
下的所有顶级声明，逐个生成 IR。

前面第 3.3 节已经详细介绍了 CodeGen 的内部机制，这里不再重复。重要的是理解：
**CodeGen 之前的所有阶段（预处理、词法、语法、语义）都是 Clang 的职责，
CodeGen 完成后，Clang 的工作结束，LLVM 接手**。

调试技巧：观察各阶段输出
============================

Clang 提供了丰富的选项来观察每个阶段的输出，这是理解编译过程的强大工具：

.. list-table:: Clang 阶段调试选项
   :header-rows: 1

   * - 阶段
     - 选项
     - 输出
   * - 预处理
     - ``clang -E hello.c``
     - 预处理后的源码文本
   * - 词法分析
     - ``clang -cc1 -dump-tokens hello.c``
     - Token 流
   * - 语法分析（AST）
     - ``clang -cc1 -ast-dump hello.c``
     - 完整的 AST 树
   * - 语法分析（简化 AST）
     - ``clang -cc1 -ast-view hello.c``
     - 用 Graphviz 生成 AST 可视化图
   * - LLVM IR
     - ``clang -S -emit-llvm hello.c``
     - LLVM IR 文本（.ll）
   * - LLVM 比特码
     - ``clang -c -emit-llvm hello.c``
     - LLVM 比特码（.bc）
   * - 汇编
     - ``clang -S hello.c``
     - 目标平台汇编（.s）
   * - 目标文件
     - ``clang -c hello.c``
     - 机器码目标文件（.o）

实战练习：观察一个简单函数的编译全过程
==========================================

创建一个 ``add.c``：

.. code-block:: c

   int add(int a, int b) {
       return a + b;
   }

逐步观察：

.. code-block:: console

   # 1. 预处理：看看 #include 展开后的样子
   $ clang -E add.c

   # 2. Token 流
   $ clang -cc1 -dump-tokens add.c

   # 3. AST
   $ clang -cc1 -ast-dump add.c

   # 4. LLVM IR
   $ clang -S -emit-llvm add.c -o add.ll
   $ cat add.ll
   ; 你应该看到：
   define i32 @add(i32 %a, i32 %b) {
       %add = add i32 %a, %b
       ret i32 %add
   }

   # 5. 汇编
   $ clang -S add.c -o add.s

用不同的 ``-O`` 级别对比 IR 的变化：

.. code-block:: console

   $ clang -O0 -S -emit-llvm add.c -o add.O0.ll
   $ clang -O2 -S -emit-llvm add.c -o add.O2.ll
   $ diff add.O0.ll add.O2.ll

你会看到 ``-O2`` 下的 IR 更简洁——这就是下一章要讲的 LLVM 优化器的工作。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
