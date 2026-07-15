.. _chapter-09-01-opt:

==========================
opt：LLVM 优化器驱动
==========================

``opt`` 是 LLVM 工具链中最核心的工具之一。它读取 LLVM IR，应用指定的 Pass，
然后输出优化后的 IR。

.. rst-class:: center

   ``opt`` 是一个"Pass 运行器"——你把 IR 和 Pass 列表给它，它帮你跑完。

.. admonition:: opt 的实用场景：生产环境中的 LLVM 工具链
   :class: tip

   虽然 ``opt`` 最常见的用途是学习和测试 Pass，但它在生产环境中也有
   意想不到的应用：

   **场景 1：定制化 -O 等级**
   Apple 的 Xcode 默认的 ``-O2`` 实际上不是 LLVM 的默认 ``-O2`` ，
   而是苹果自己调过参数的管道。通过 ``opt -pass-pipeline`` 可以精确
   控制哪些 Pass 运行、什么顺序运行。

   **场景 2：调试优化器**
   ``opt -print-after-all`` 这个选项被 LLVM 开发者称为"最强大的调试武器"。
   它在每个 Pass 之后都打印 IR，让你看到 IR 从输入到输出的 **每一帧变化** 。
   加上 ``-debug-only=pass-name`` 可以只看特定 Pass 的调试日志。

   **场景 3：LLVM 测试基础设施**
   LLVM 的回归测试套件（ ``test/Transforms/`` 目录下数千个 ``.ll`` 文件）
   几乎全部通过 ``opt`` 驱动。一个典型的测试文件是这样：
   
   ``; RUN: opt -pass-name < %s | FileCheck %s``

   这意味着 ``opt`` 是 LLVM 质量保证体系的核心——每天运行数百万次。

   **场景 4：优化考古**
   想知道某个 Pass 在某个版本做了什么优化？用 ``opt -print-before=pass-name``
   和 ``opt -print-after=pass-name`` 可以对比优化前后的 IR。这在
   性能调优和 Pass 开发中非常有用。

基本用法
============

.. code-block:: console

   # 运行 mem2reg Pass
   $ opt -passes=mem2reg input.ll -S -o output.ll

   # 运行多个 Pass（逗号分隔）
   $ opt -passes='mem2reg,instcombine,gvn' input.ll -S

   # 运行默认优化管道
   $ opt -passes='default<O2>' input.ll -S

   # 读取比特码，输出文本 IR
   $ opt input.bc -S -o output.ll

参数说明：

- ``-passes`` ：指定要运行的 Pass 管道（New PM 格式）
- ``-S`` ：输出文本格式 IR（.ll），不指定则输出比特码（.bc）
- ``-o`` ：指定输出文件，不指定则输出到 stdout

``opt`` 的输入输出都是 IR，这意味着 **你可以把 ``opt`` 的输出再喂给
另一个 ``opt``**。这种"管道式"设计使 ``opt`` 成为 IR 变换的"瑞士军刀"——
你可以把多个 ``opt`` 调用串联起来，逐步调试每一步的变换效果。

Pass 管道语法
================

``opt`` 的 ``-passes`` 参数支持丰富的管道描述语法，这是 New PM 的一大亮点：

.. code-block:: console

   # 单个 Pass
   -passes=mem2reg

   # Pass 序列（逗号分隔）
   -passes='mem2reg,instcombine,gvn'

   # 嵌套管道（{} 用于分组）
   -passes='function(mem2reg,instcombine),module(gvn)'

   # 默认优化等级
   -passes='default<O2>'
   -passes='default<O3>'

   # 在默认管道前后插入 Pass
   -passes='default<O2>,my-pass'

为什么 ``-passes`` 需要支持嵌套？因为 LLVM 的 Pass 有不同作用域：
**Function Pass** 在每个函数上运行，**Module Pass** 在整个模块上运行。
嵌套语法 ``function(mem2reg,instcombine)`` 明确表达了"在函数作用域内
依次运行 mem2reg 和 instcombine"。

这与 Legacy PM 的 ``-mem2reg -instcombine -gvn`` 扁平语法形成对比——
New PM 的嵌套语法让 Pass 管道的 **结构显式化**，管道结构本身就是
文档。

加载 Pass 插件
====================

LLVM 15+ 使用 New Pass Manager 时，通过 ``-load-pass-plugin`` 加载自定义 Pass：

.. code-block:: console

   # 编译 Pass 插件
   $ clang++ -shared -fPIC -o libMyPass.so MyPass.cpp \
       `llvm-config --cxxflags --ldflags --libs`

   # 加载并运行
   $ opt -load-pass-plugin=./libMyPass.so \
         -passes='my-pass' input.ll -S

Legacy PM（可选）仍然使用 ``-load`` ：

.. code-block:: console

   $ opt -load ./libMyLegacyPass.so -my-pass input.ll -S

Pass 插件机制是 LLVM 模块化设计的体现：**Pass 不需要编译进 ``opt`` 二进制**，
而是作为动态库加载。这有两层意义：

1. **开发者角度**：开发新 Pass 时不需要重新编译整个 LLVM，只需编译
   一个 ``.so`` 文件，极大缩短了开发迭代周期
2. **用户角度**：可以按需加载 Pass，不需要的 Pass 不加载，减少内存占用

调试输出
============

``opt`` 提供了丰富的调试选项，让 IR 变换的过程完全透明：

.. code-block:: console

   # 查看 Pass 的执行时间统计
   $ opt -passes='default<O2>' -time-passes input.ll -S -o /dev/null

   # 在每个 Pass 之前打印 IR
   $ opt -passes='mem2reg,instcombine' -print-before-all input.ll -S

   # 在每个 Pass 之后打印 IR
   $ opt -passes='mem2reg,instcombine' -print-after-all input.ll -S

   # 只打印特定函数的变化
   $ opt -passes='mem2reg,instcombine' \
         -filter-print-funcs='myFunc' input.ll -S

   # 查看所有可用的 Pass
   $ opt --print-passes

   # 查看 Pass 管道的结构
   $ opt -passes='default<O2>' -print-pipeline-passes

``-print-after-all`` 是 LLVM 开发者最常用的调试选项。它会在每个 Pass
之后打印 IR 的快照，就像电影的逐帧播放。如果你在开发一个 Pass 时发现
输出不符合预期，先用 ``-print-after-all`` 找到"IR 第一次出错的 Pass"，
然后只关注那个 Pass 的调试输出。

结合 ``-print-before-all`` 和 ``-print-after-all``，你可以看到
**每个 Pass 的输入和输出**——这正是"夹叙夹议"中"叙"的极致体现：
IR 的每一帧变化都是可观察的。

统计信息
============

.. code-block:: console

   # 启用统计信息
   $ opt -passes='gvn' -stats input.ll -S -o /dev/null

   # 输出示例：
   # 3 gvn - Number of instructions deleted
   # 2 gvn - Number of loads deleted
   # 1 gvn - Number of PHIs deleted

# 查看 Pass 管道的执行顺序
   $ opt -passes='default<O2>' -print-pipeline-passes

``-stats`` 输出的是 Pass 内部的计数器——每个 Pass 可以定义自己的统计
指标（删除了多少条指令、做了多少次内联等）。这些数字是衡量 Pass 效果的
"硬数据"，比"感觉上优化了"可靠得多。

典型用法：对比优化前后
==============================

.. code-block:: console

   # 生成优化前的 IR
   $ clang -S -emit-llvm -O0 hello.c -o before.ll

   # 运行优化
   $ opt -passes='default<O2>' before.ll -S -o after.ll

   # 对比
   $ diff before.ll after.ll

   # 或者直接用 -O2 生成优化后的 IR
   $ clang -S -emit-llvm -O2 hello.c -o optimized.ll

这个工作流是学习 LLVM 优化最有效的方式：**写一段 C 代码，生成优化前后
的 IR，用 ``diff`` 逐行对比**。看 ``diff`` 的输出，问自己两个问题：

1. "优化器删除了什么？"——理解每个 Pass 的"删除"能力
2. "优化器做了什么变换？"——理解每个 Pass 的"变换"能力

如果你能解释 ``diff`` 输出中的每一行变化，你就真正理解了 LLVM 的优化。

opt 的源码位置
====================

``opt`` 的源码是一个相对较小的文件，展示了如何创建 PassBuilder 和运行 Pass：

`llvm/tools/opt/opt.cpp <file:///workspace/llvm-project/llvm/tools/opt/opt.cpp>`__

它的核心逻辑只有几十行：

.. code-block:: cpp

   // opt 的核心逻辑（LLVM 17+）
   PassBuilder PB(TM);
   ModulePassManager MPM;

   // 根据 -passes 参数解析管道
   if (auto Err = PB.parsePassPipeline(MPM, PassesStr)) {
       errs() << "Failed to parse pass pipeline: "
              << toString(std::move(Err)) << "\n";
       return 1;
   }

   // 运行 Pass 管道
   MPM.run(M, MAM);

这段代码展示了 LLVM 架构的一个重要设计：**PassBuilder 是 Pass 管理的
核心入口**。它负责三件事：

1. **解析**：将 ``-passes`` 字符串解析为 Pass 对象
2. **构建**：创建 PassManager 并注册 Pass
3. **运行**：执行整个 Pass 管道

这种"解析-构建-运行"的三段式设计，使得 Pass 管道可以灵活配置——
这正是 ``opt`` 作为"Pass 运行器"的底层实现。