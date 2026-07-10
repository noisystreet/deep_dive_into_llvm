.. _chapter-09-04-llvm-dis-and-asm:

==========================
llvm-dis 与 llvm-as
==========================

``llvm-dis`` 和 ``llvm-as`` 是 LLVM IR 两种格式之间的转换器：
比特码（``.bc`` ）和文本格式（``.ll`` ）。

.. rst-class:: center

   两种格式在语义上完全等价，只是用途不同。理解它们的关系就是理解
   LLVM IR 的"双面性"。

为什么需要两种格式？
=========================

LLVM IR 有**三种表示形式** ，它们在语义上完全等价：

.. list-table:: LLVM IR 的三种形式
   :header-rows: 1

   * - 形式
     - 文件后缀
     - 特点
     - 使用场景
   * - **文本格式**
     - ``.ll``
     - 人类可读，便于调试
     - 开发、调试、学习
   * - **比特码**
     - ``.bc``
     - 紧凑、加载快、适合存储和传输
     - 分发、链接、缓存
   * - **内存表示**
     - （不持久化）
     - 高效运行时操作
     - opt/llc/lli 运行时

llvm-as：文本 → 比特码
============================

.. code-block:: console

   # 基本用法
   $ llvm-as input.ll -o output.bc

   # 省略 -o，输出文件名从输入推导（input.bc）
   $ llvm-as input.ll

   # 从 stdin 读取
   $ cat input.ll | llvm-as -o output.bc

   # 验证模式（只检查语法，不输出文件）
   $ llvm-as input.ll -o /dev/null

llvm-as 的"编译"过程很简单：解析文本 IR，构建内存中的 ``llvm::Module`` 对象，
然后序列化为比特码。如果 IR 有语法错误，llvm-as 会报告错误行号和位置：

.. code-block:: text

   $ cat bad.ll
   define i32 @f(i32 %a) {
       %b = ad i32 %a, 1    ; "ad" 是非法指令
       ret i32 %b
   }
   $ llvm-as bad.ll
   llvm-as: bad.ll:2:10: error: expected instruction opcode
       %b = ad i32 %a, 1
            ^

llvm-dis：比特码 → 文本
============================

.. code-block:: console

   # 基本用法
   $ llvm-dis input.bc -o output.ll

   # 省略 -o，从输入推导（input.ll）
   $ llvm-dis input.bc

   # 从 stdin 读取比特码
   $ cat input.bc | llvm-dis -o output.ll

比特码格式的版本兼容性
==============================

LLVM 比特码格式在不同版本之间可能不兼容。LLVM 22 的 ``llvm-dis`` 可能无法
读取 LLVM 18 生成的比特码。解决方法：

.. code-block:: console

   # 查看比特码的 LLVM 版本
   $ llvm-bcanalyzer input.bc | head -5

   # 使用 llvm-as 重新编译文本 IR
   $ llvm-as input.ll -o input.bc

实际开发中，建议将 LLVM IR 以文本格式（``.ll`` ）保存在版本控制系统中，
因为它可读、可 diff，且不受比特码版本兼容性的影响。

llvm-extract：从模块中提取函数
=====================================

.. code-block:: console

   # 从模块中提取指定函数
   $ llvm-extract -func=add input.ll -o add_only.ll

   # 提取多个函数
   $ llvm-extract -func=add -func=sub input.ll

   # 删除指定函数（提取剩下的部分）
   $ llvm-extract -delete -func=debug_func input.ll

这在调试时非常有用——你可以从一个大模块中只提取感兴趣的少数函数。

llvm-link：链接多个 IR 模块
=================================

.. code-block:: console

   # 链接多个 IR 模块
   $ llvm-link foo.ll bar.ll -o combined.ll

   # 链接比特码
   $ llvm-link foo.bc bar.bc -o combined.bc

   # 手动指定链接后的输出格式
   $ llvm-link foo.ll bar.ll -S -o combined.ll

llvm-link 的行为类似于传统的链接器，但工作在 IR 层面：
它合并多个 Module 的全局变量、函数声明和元数据，
并解析跨模块的符号引用。

llvm-bcanalyzer：比特码分析
==================================

一个有用的调试工具：

.. code-block:: console

   # 查看比特码的统计信息
   $ llvm-bcanalyzer input.bc

   # 查看数据布局
   $ llvm-bcanalyzer -dump input.bc

实战：比特码分发
====================

在需要分发 LLVM IR 的场景中（如 OpenCL 的 SPIR-V、WebAssembly 的 LLVM 后端），
通常的流程是：

.. code-block:: console

   # 1. 编译为比特码（给用户分发）
   $ clang -c -emit-llvm -O2 kernel.cl -o kernel.bc

   # 2. 用户端：比特码 → 文本（调试时）
   $ llvm-dis kernel.bc -o kernel.ll

   # 3. 用户端：比特码 → 优化 → 本地执行
   $ opt kernel.bc -passes='default<O2>' -o kernel_opt.bc
   $ llc kernel_opt.bc -filetype=obj -o kernel.o

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
