.. _chapter-03-02-ast-structure:

==========================
AST 结构
==========================

上一节我们提到 Clang 是"库化设计"的——每个编译阶段都是独立的库。那么当你写下一段
C 代码后，Clang 首先把它变成了什么？答案是**抽象语法树** （Abstract Syntax Tree, AST）。

.. rst-class:: center

   拿一棵树来表示你的代码——每个节点是语法结构（函数、变量、表达式），
   树的结构反映了语言的嵌套关系。

从一段 C 代码看 AST
======================

假设我们有这样一段简单的代码：

.. code-block:: c

   int add(int a, int b) {
       int result = a + b;
       return result;
   }

Clang 解析这段代码后，会构建出一棵 AST。你可以用 ``clang -cc1 -ast-dump`` 直接查看：

.. code-block:: console

   $ clang -cc1 -ast-dump add.c

输出的 AST 大致如下（简化）：

.. code-block:: text

   TranslationUnitDecl
   └── FunctionDecl 'add(int, int) -> int'
       ├── ParmVarDecl 'int a'
       ├── ParmVarDecl 'int b'
       └── CompoundStmt
           ├── DeclStmt
           │   └── VarDecl 'int result'
           │       └── BinaryOperator '+'
           │           ├── ImplicitCastExpr 'a' (LValueToRValue)
           │           │   └── DeclRefExpr 'a'
           │           └── ImplicitCastExpr 'b' (LValueToRValue)
           │               └── DeclRefExpr 'b'
           └── ReturnStmt
               └── ImplicitCastExpr 'result' (LValueToRValue)
                   └── DeclRefExpr 'result'

这棵树**忠实反映了 C 语言的语法结构** ：

- 顶层是 ``TranslationUnitDecl`` （翻译单元，即一个源文件）
- 下一层是 ``FunctionDecl`` （函数声明/定义）
- 函数体内是 ``CompoundStmt`` （复合语句，即 ``{}`` 中的内容）
- 变量声明对应 ``DeclStmt`` + ``VarDecl``
- 赋值/算术对应 ``BinaryOperator``
- 变量引用对应 ``DeclRefExpr``
- ``return`` 对应 ``ReturnStmt``

重要特征：**AST 包含了源码中所有的语法信息，但去掉了不必要的细节** （如分号、
括号等标点符号不再有单独的节点，它们隐含在节点类型中）。

核心 AST 节点
=================

Clang 的 AST 节点大致分为三类：

Expr（表达式）
------------------------

表达式节点代表一个**计算值的代码片段** 。表达式可以嵌套——比如 ``a + b * c`` 会
生成一棵表达式子树。

.. list-table:: 常见 Expr 子类
   :header-rows: 1

   * - 节点类型
     - 说明
     - 示例源码
   * - ``DeclRefExpr``
     - 引用一个变量/函数
     - ``x`` 、``printf``
   * - ``IntegerLiteral``
     - 整数字面量
     - ``42`` 、``0xFF``
   * - ``BinaryOperator``
     - 二元运算
     - ``a + b`` 、``x != 0``
   * - ``UnaryOperator``
     - 一元运算
     - ``-x`` 、``!flag`` 、``*ptr``
   * - ``CallExpr``
     - 函数调用
     - ``foo(x, y)``
   * - ``ImplicitCastExpr``
     - 隐式类型转换
     - ``int x = 3.14`` （double → int）
   * - ``ArraySubscriptExpr``
     - 数组下标访问
     - ``arr[i]``
   * - ``MemberExpr``
     - 结构体/类成员访问
     - ``s.field`` 、``p->field``

Decl（声明）
------------------------

声明节点代表一个**名字的引入**——变量、函数、类型、命名空间等。

.. list-table:: 常见 Decl 子类
   :header-rows: 1

   * - 节点类型
     - 说明
     - 示例源码
   * - ``FunctionDecl``
     - 函数声明/定义
     - ``int add(int a, int b)``
   * - ``VarDecl``
     - 变量声明
     - ``int x = 42;``
   * - ``ParmVarDecl``
     - 函数参数
     - 函数括号中的 ``a`` 、``b``
   * - ``RecordDecl``
     - 结构体/类声明
     - ``struct Point { ... }``
   * - ``FieldDecl``
     - 结构体/类成员
     - ``int x;`` 在结构体中
   * - ``TypedefDecl``
     - 类型别名
     - ``typedef int i32;``
   * - ``EnumDecl``
     - 枚举声明
     - ``enum Color { RED, GREEN }``

Stmt（语句）
------------------------

语句节点代表一个**完整的执行步骤** 。语句通常包含表达式，或嵌套其他语句。

.. list-table:: 常见 Stmt 子类
   :header-rows: 1

   * - 节点类型
     - 说明
     - 示例源码
   * - ``CompoundStmt``
     - 复合语句（代码块）
     - ``{ ... }``
   * - ``IfStmt``
     - 条件分支
     - ``if (x > 0) { ... }``
   * - ``ForStmt`` / ``WhileStmt`` / ``DoStmt``
     - 循环语句
     - ``for (;;)`` 、``while(1)``
   * - ``ReturnStmt``
     - 返回语句
     - ``return x;``
   * - ``SwitchStmt``
     - switch 语句
     - ``switch(n) { case 1: ... }``
   * - ``BreakStmt`` / ``ContinueStmt``
     - 跳转语句
     - ``break;`` 、``continue;``

ASTContext 与 SourceManager
=============================

这两个类是理解 Clang AST 操作的关键基础设施。

**ASTContext** 是整个 AST 的**所有者** 和**工厂** 。

- 所有 AST 节点（``Decl`` 、``Stmt`` 、``Type`` 、``QualType`` ）都由 ``ASTContext`` 分配和管理
- 它缓存了常用的类型（``int`` 、``char`` 、``void`` 等），避免了重复创建
- 可以通过 ``ASTContext::getIntTypeForBitWidth()`` 、``ASTContext::getPointerType()`` 等方法创建和查询类型

``ASTContext`` 的定义在源码位置：
`clang/include/clang/AST/ASTContext.h <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/clang/include/clang/AST/ASTContext.h>`__

**SourceManager** 负责管理**源码位置信息** （文件、行号、列号）。

- 每个 AST 节点都关联了一个 ``SourceLocation`` ，记录了它在源码中的位置
- ``SourceManager`` 可以获取某一行/列的源码文本，也可以判断两个位置的前后关系
- 这就是 Clang 能给出精确错误位置的底层机制

.. code-block:: cpp

   // SourceManager 提供了以下几个关键接口：
   SourceLocation loc = decl->getLocation();
   unsigned line = SM.getSpellingLineNumber(loc);
   unsigned col  = SM.getSpellingColumnNumber(loc);
   StringRef filename = SM.getFilename(loc);

使用 RecursiveASTVisitor 遍历 AST
=====================================

Clang 提供了一个方便的模式来遍历整个 AST：**RecursiveASTVisitor** 。

假设我们想找出源码中所有的函数定义：

.. code-block:: cpp

   #include "clang/AST/RecursiveASTVisitor.h"

   class MyVisitor : public RecursiveASTVisitor<MyVisitor> {
   public:
       bool VisitFunctionDecl(FunctionDecl *FD) {
           // 每个 FunctionDecl 都会回调到这里
           llvm::outs() << "Found function: " << FD->getNameInfo().getName() << "\n";
           return true;  // 返回 true 继续遍历
       }
   };

   // 使用方法：
   MyVisitor Visitor;
   Visitor.TraverseDecl(Context.getTranslationUnitDecl());

``RecursiveASTVisitor`` 的 CRTP（奇异递归模板模式）设计使得你可以只覆盖你关心的
回调函数——不覆盖的方法会走默认行为（继续递归子节点）。

使用 ``clang -ast-dump`` 查看 AST
=====================================

如前所述，可以直接在命令行打印 AST：

.. code-block:: console

   # 查看完整 AST
   $ clang -cc1 -ast-dump hello.c

   # 不展开系统头文件（更简洁）
   $ clang -cc1 -ast-dump -fno-modules hello.c

   # 只看某个函数的 AST
   $ clang -cc1 -ast-dump hello.c | grep -A 30 "FunctionDecl.*add"

这个命令在调试 Clang 相关工具时非常有用——你不确定某个代码结构生成什么 AST 节点时，
直接 ``ast-dump`` 看一下就知道了。

ASTMatcher 与 clang-query
=====================================

对于更复杂的 AST 搜索需求，Clang 提供了 **ASTMatcher** DSL，以及配套的交互式工具
**clang-query** 。

例如，想查找所有 ``int`` 类型的变量声明：

.. code-block:: cpp

   auto Matcher = varDecl(hasType(isInteger())).bind("intVar");

对应的 ``clang-query`` 交互：

.. code-block:: text

   $ clang-query hello.c --
   clang-query> match varDecl(hasType(isInteger()))
   Match #1:
   /path/to/hello.c:3:5: note: "root" binds here
       int result = a + b;
       ^~~~~~~~~~

ASTMatcher 的匹配器可以组合出非常复杂的查询条件，比如"找到所有名字以 'test' 开头
的无返回值函数调用"：

.. code-block:: cpp

   callExpr(
       callee(functionDecl(hasName("::test*"))),
       returns(voidType())
   )

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
