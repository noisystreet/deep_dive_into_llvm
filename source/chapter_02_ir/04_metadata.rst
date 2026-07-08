.. _chapter-02-04-metadata:

==========================
元数据系统
==========================

前面的章节中我们讨论的所有 IR 元素都是程序的**语义内容**——它们直接影响执行结果。
但 LLVM IR 中还有一类特殊的元素，它们**不影响**执行语义，但携带额外的信息——
这就是**元数据**（Metadata）。

元数据在 IR 中以 ``!`` 为前缀：

.. code-block:: llvm

   !0 = !{ !"hello" }       ; 元数据节点
   !1 = !DIFile(...)        ; 调试信息元数据
   %result = add i32 %a, %b, !dbg !0   ; 指令关联的元数据

元数据分为两类：

1. **附着型**\ （Attached Metadata）：附加在指令上的元数据（如 ``!dbg``、\ ``!tbaa``）
2. **命名元数据**\ （Named Metadata）：模块级别的元数据声明（如 ``!llvm.dbg.cu``）

为什么需要元数据？
====================

元数据连接了**源码世界**和**IR 世界**的信息鸿沟。当编译器优化代码时，它需要
知道变量的活跃范围以便生成调试信息，需要知道循环的源文件行号以便报告编译警告。
元数据携带这些信息，且优化器在处理 IR 的同时会维护和更新它们。

元数据的类型
================

**MDNode -- 元数据节点**

.. code-block:: llvm

   !0 = !{ !"name", i32 42, !1 }

在 C++ API 中：

.. code-block:: cpp

   MDNode *N = MDNode::get(Context, {
       MDString::get(Context, "name"),
       ConstantAsMetadata::get(ConstantInt::get(...))
   });

**MDString -- 元数据字符串**

.. code-block:: llvm

   !0 = !{ !"hello, world" }

**ValueAsMetadata -- 将 IR 值包装为元数据**

.. code-block:: llvm

   !0 = !{ i32 %val }

元数据与优化
================

元数据**不会影响执行语义**。优化器可以安全地将一条指令替换为另一条，即使它们
的元数据不同：

.. code-block:: llvm

   ; 这两条指令语义等价
   %a = add i32 %x, %y, !dbg !0
   %b = add i32 %x, %y, !dbg !1

**常见的附着元数据标签：**

- ``!dbg`` -- 源代码位置信息（行号、列号、文件）
- ``!tbaa`` -- 基于类型的别名分析信息
- ``!alias.scope`` / ``!noalias`` -- 别名作用域信息
- ``!range`` -- 值的取值范围信息（帮助优化器做边界检查消除）
- ``!prof`` -- 性能分析（PGO）信息
- ``!nosanitize`` -- 标记不需要消毒检查的指令

**例：!tbaa**

.. code-block:: llvm

   %val = load i32, ptr %int_ptr, !tbaa !2
   store float 1.0, ptr %float_ptr, !tbaa !3
   ; 优化器知道 int* 和 float* 不会指向同一个对象

**例：!range**

.. code-block:: llvm

   %idx = load i32, ptr %ptr, !range !4
   ; !4 = !{ i32 0, i32 100 }  -> %idx 在 [0, 100) 范围内

命名元数据
==============

.. code-block:: llvm

   !llvm.dbg.cu = !{!0, !1}       ; 编译单元列表
   !llvm.module.flags = !{!2}     ; 模块标志
   !llvm.ident = !{!3}            ; 编译器版本

.. code-block:: cpp

   NamedMDNode *NMD = M->getNamedMetadata("llvm.dbg.cu");

元数据的实现
================

元数据以 ``Metadata`` 类为基类（``llvm/include/llvm/IR/Metadata.h``）：

.. code-block:: cpp

   class Metadata {
     enum MetadataKind {
       MDTupleKind, DILocationKind, DIFileKind, DISubprogramKind, ...
     };
   };

``MDNode`` 使用引用计数管理生命周期。相同的元数据节点在同一个上下文中只会
存在一份（uniquification）。通过 ``ReplaceableMetadataImpl`` 机制，当 IR 值
被删除时，所有引用它的元数据节点也会被自动更新。