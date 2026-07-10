.. _chapter-02-02-instruction-set:

==========================
IR 指令集详解
==========================

上一节我们了解了 IR 的基本语法和类型系统。这一节深入 IR 指令集——所有的
指令类型、它们的语义和典型用法。

LLVM IR 的指令在 ``llvm/include/llvm/IR/Instructions.h`` 中定义，
每条指令对应一个 C++ 类，继承自 ``Instruction`` 。

.. admonition:: LLVM IR 指令的"家族"划分
   :class: note

   LLVM IR 有 60+ 种指令，但可按语义分为几个"家族"：

   - **Terminator** — 改变控制流：``br`` 、 ``ret`` 、 ``switch``
   - **BinaryOperator** — 二元运算：``add`` 、 ``fmul`` 、 ``and``
   - **Memory** — 内存访问：``load`` 、 ``store`` 、 ``alloca`` 、 ``getelementptr``
   - **Cast** — 类型转换：``zext`` 、 ``bitcast`` 、 ``ptrtoint``
   - **Other** — 调用、PHI、向量操作等

   理解这个分类对读 Pass 源码至关重要——``InstCombiner`` 按家族分派，
   ``SelectionDAGBuilder`` 按家族建 DAG 节点。遇到不认识的指令，
   先判断它属于哪个家族，再查对应的处理逻辑。

内存指令
================

**alloca -- 分配栈内存**

.. code-block:: llvm

   %ptr = alloca i32           ; 分配一个 i32
   %ptr = alloca i32, align 8  ; 指定对齐
   %arr = alloca [10 x i32]    ; 分配数组

``alloca`` 在函数栈帧上分配空间，函数返回时自动释放。在 ``-O0`` 下 Clang
为每个局部变量生成一个 ``alloca`` ；优化后 ``mem2reg`` Pass 会将其提升为
SSA 寄存器。

**load -- 从内存读取**

.. code-block:: llvm

   %val = load i32, ptr %ptr        ; 从 ptr 读取 i32
   %val = load i32, ptr %ptr, align 4

**store -- 写入内存**

.. code-block:: llvm

   store i32 %val, ptr %ptr         ; 将 %val 写入 ptr
   store i32 %val, ptr %ptr, align 4

**使用模式：alloca + store + load**

在未优化的 IR 中，这三个指令经常组合出现：

.. code-block:: llvm

   ; C: int x = 42; int y = x + 1;
   %x = alloca i32, align 4
   store i32 42, ptr %x, align 4
   %0 = load i32, ptr %x, align 4
   %y = add i32 %0, 1

经过 ``mem2reg`` 优化后，变为：

.. code-block:: llvm

   %y = add i32 42, 1   ; alloca 被消除，常量传播

算术指令
================

**整数算术指令：**

.. list-table::
   :header-rows: 1

   * - 指令
     - 含义
     - 示例
   * - ``add`` / ``sub`` / ``mul``
     - 加减乘（可带 ``nsw``/``nuw`` 标记）
     - ``%r = add nsw i32 %a, %b``
   * - ``udiv`` / ``sdiv``
     - 无/有符号除法
     - ``%r = sdiv i32 %a, %b``
   * - ``urem`` / ``srem``
     - 无/有符号取模
     - ``%r = srem i32 %a, %b``
   * - ``shl`` / ``lshr`` / ``ashr``
     - 左移/逻辑右移/算术右移
     - ``%r = shl i32 %a, 1``
   * - ``and`` / ``or`` / ``xor``
     - 按位与/或/异或
     - ``%r = and i32 %a, %b``
   * - ``icmp``
     - 整数比较（eq/ne/sgt/slt/ugt/ult 等）
     - ``%r = icmp eq i32 %a, %b``

``nsw``\ （No Signed Wrap）标记表示不会发生有符号溢出，允许优化器做更激进的代数变换。

**浮点算术指令：**

.. list-table::
   :header-rows: 1

   * - 指令
     - 含义
     - 示例
   * - ``fadd`` / ``fsub`` / ``fmul`` / ``fdiv`` / ``frem``
     - 浮点运算
     - ``%r = fadd float %a, %b``
   * - ``fcmp``
     - 浮点比较（oeq/ogt/olt/une/uno 等）
     - ``%r = fcmp oeq float %a, %b``

浮点比较谓词分为有序（``o`` 前缀）和无序（``u`` 前缀）两组，因为要考虑 NaN。

控制流指令
================

控制流指令都是**基本块终止指令**——必须是基本块的最后一条指令。

**br -- 无条件或条件分支**

.. code-block:: llvm

   br label %target                    ; 无条件跳转
   br i1 %cond, label %t, label %f     ; 条件跳转

**switch -- 多路分支**

.. code-block:: llvm

   switch i32 %val, label %default [
       i32 0, label %case0
       i32 1, label %case1
   ]

**ret -- 函数返回**

.. code-block:: llvm

   ret void
   ret i32 %result

**phi -- phi 节点**

.. code-block:: llvm

   %result = phi i32 [ %val1, %bb1 ], [ %val2, %bb2 ]

**常见的控制流模式：**

.. code-block:: llvm
   :caption: if-else 模式

   define i32 @if_else(i32 %x) {
   entry:
     %cmp = icmp sgt i32 %x, 0
     br i1 %cmp, label %then, label %else
   then:
     br label %merge
   else:
     br label %merge
   merge:
     %a = phi i32 [ 1, %then ], [ 2, %else ]
     ret i32 %a
   }

.. code-block:: llvm
   :caption: while 循环模式

   define i32 @while_loop(i32 %n) {
   entry:
     br label %header
   header:
     %i = phi i32 [ 0, %entry ], [ %i_next, %body ]
     %sum = phi i32 [ 0, %entry ], [ %sum_next, %body ]
     %cond = icmp slt i32 %i, %n
     br i1 %cond, label %body, label %exit
   body:
     %sum_next = add i32 %sum, %i
     %i_next = add i32 %i, 1
     br label %header
   exit:
     ret i32 %sum
   }

聚合操作指令
================

.. code-block:: llvm

   ; 从结构体提取成员
   %m = extractvalue { i32, i64 } %val, 0

   ; 构造新的聚合值
   %new = insertvalue { i32, i64 } %old, i32 %x, 0

   ; 向量操作
   %e = extractelement <4 x i32> %vec, i32 0
   %v = insertelement <4 x i32> %vec, i32 %val, i32 2
   %s = shufflevector <4 x i32> %a, <4 x i32> %b, <4 x i32> <i32 0, i32 4, i32 1, i32 5>

类型转换指令
================

LLVM 要求所有类型转换都**显式** 写出：

.. list-table::
   :header-rows: 1

   * - 指令
     - 含义
     - 示例
   * - ``trunc`` / ``zext`` / ``sext``
     - 整数截断/零扩展/符号扩展
     - ``%r = zext i8 %x to i32``
   * - ``fptrunc`` / ``fpext``
     - 浮点精度降低/提升
     - ``%r = fptrunc double %x to float``
   * - ``fptoui`` / ``fptosi`` / ``uitofp`` / ``sitofp``
     - 整数与浮点互转
     - ``%r = sitofp i32 %x to double``
   * - ``ptrtoint`` / ``inttoptr``
     - 指针与整数互转
     - ``%r = ptrtoint ptr %p to i64``
   * - ``bitcast``
     - 重新解释位模式
     - ``%r = bitcast float %x to i32``

GEP 详解
================

**GetElementPtr（GEP）** 是 LLVM IR 中最容易被误解的指令。
它**不访问内存** ，只计算指针经过若干索引后的地址。

**基本语法：**

.. code-block:: none

   %result = getelementptr <elem_type>, ptr <base>, <index1>, <index2>, ...

GEP 的索引是**从外层到内层** 的。第一个索引作用于指针本身，后续索引依次深入。

**例 1：一维数组**

.. code-block:: llvm

   @arr = global [10 x i32] zeroinitializer
   %ptr = getelementptr [10 x i32], ptr @arr, i64 0, i64 3
   store i32 42, ptr %ptr   ; arr[3] = 42

**例 2：结构体**

.. code-block:: llvm

   %struct.S = type { i32, float }
   @s = global %struct.S zeroinitializer
   %ptr = getelementptr %struct.S, ptr @s, i64 0, i32 1  ; &s.b

**GEP 的步长由第一个参数的类型决定：**

.. code-block:: llvm

   ; 步长 = sizeof(i32) = 4 字节
   %p1 = getelementptr i32, ptr %base, i64 3

   ; 步长 = sizeof([10 x i32]) = 40 字节
   %p2 = getelementptr [10 x i32], ptr %base, i64 3

GEP 的源码实现是 ``GetElementPtrInst`` 类，定义在
``llvm/include/llvm/IR/Instructions.h`` 中。