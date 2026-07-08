.. _chapter-02-05-debug-info:

==========================
调试信息
==========================

调试信息是元数据系统中最重要、最复杂的应用。加上 ``-g`` 编译时，Clang 会在
IR 中生成大量调试元数据，将 IR 指令与源代码位置、变量名、类型信息关联起来。

.. code-block:: bash

   clang -S -emit-llvm -g hello.c -o hello.debug.ll

加上 ``-g`` 后，生成的 IR 会比不加时膨胀 3-5 倍——多出来的部分全是调试元数据。

调试信息的结构层次
========================

调试信息组织为树状结构，每个编译单元（``!DIBuCompileUnit``）对应一个源文件：

- **文件信息**\ （\ ``!DIFile``）：文件名、目录路径
- **子程序信息**\ （\ ``!DISubprogram``）：函数名、返回类型、参数列表
- **局部变量信息**\ （\ ``!DILocalVariable``）：变量名、类型、参数序号
- **类型信息**\ （\ ``!DIBasicType``、\ ``!DICompositeType``）：基本类型和复合类型
- **位置信息**\ （\ ``!DILocation``）：行号和列号

核心调试节点
================

**!DIBuCompileUnit**

.. code-block:: none

   !0 = !DIBuCompileUnit(
     language: DW_LANG_C99,
     file: !1,
     producer: "clang version 22.1.8",
     emissionKind: FullDebug
   )

**!DIFile**

.. code-block:: llvm

   !1 = !DIFile(filename: "hello.c", directory: "/home/user/project")

**!DISubprogram**

.. code-block:: none

   !2 = !DISubprogram(
     name: "add", scope: !1, file: !1, line: 1,
     type: !3, scopeLine: 1, spFlags: DISPFlagDefinition
   )

**!DILocalVariable**

.. code-block:: llvm

   !4 = !DILocalVariable(name: "a", arg: 1, scope: !2, file: !1, type: !5)

**!DIBasicType**

.. code-block:: none

   !5 = !DIBasicType(name: "int", size: 32, encoding: DW_ATE_signed)

**!DILocation** -- 附着在指令的 ``!dbg`` 上：

.. code-block:: llvm

   %add = add nsw i32 %a, %b, !dbg !6

调试信息与优化
================

优化会改变或消除源代码中的结构，而调试信息需要保留这种结构。这是一个根本矛盾。

**llvm.dbg.value -- 跟踪 SSA 值**

当 ``mem2reg`` 将 ``alloca`` 提升为 SSA 值时，生成 ``llvm.dbg.value``
记录变量的当前值：

.. code-block:: llvm

   call void @llvm.dbg.value(metadata i32 %x, metadata !4,
                             metadata !DIExpression())

**llvm.dbg.declare -- 声明变量位置（主要用于 -O0）**

.. code-block:: llvm

   %a = alloca i32, align 4
   call void @llvm.dbg.declare(metadata ptr %a, metadata !4,
                               metadata !DIExpression())

**DIExpression -- 值表达式**

当调试器需要的值与 IR 值不完全一致时，用 ``DIExpression`` 描述变换：

.. code-block:: none

   call void @llvm.dbg.value(metadata i32 %x, metadata !4,
       metadata !DIExpression(DW_OP_plus_uconst, 1))
   ; a 的值是 %x + 1

源码实现
================

调试信息对应的类位于 ``llvm/include/llvm/IR/DebugInfoMetadata.h``：

.. code-block:: cpp

   class DILocation : public MDNode {
     unsigned Line, Column;
   };
   class DISubprogram : public DIScope { StringRef Name; };
   class DILocalVariable : public DINode { StringRef Name; unsigned Arg; };

.. warning::

   调试元数据会增加 IR 体积和编译时间。生产环境常见做法：用 ``-O2 -g`` 编译，
   然后通过 ``strip`` 或 ``objcopy`` 分离调试信息。