.. _chapter-09-01-opt:

==========================
opt：LLVM 优化器驱动
==========================

``opt`` 是 LLVM 工具链中最核心的工具之一。它读取 LLVM IR，应用指定的 Pass，
然后输出优化后的 IR。

.. rst-class:: center

   ``opt`` 是一个"Pass 运行器"——你把 IR 和 Pass 列表给它，它帮你跑完。

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

- ``-passes``：指定要运行的 Pass 管道（New PM 格式）
- ``-S``：输出文本格式 IR（.ll），不指定则输出比特码（.bc）
- ``-o``：指定输出文件，不指定则输出到 stdout

Pass 管道语法
================

``opt`` 的 ``-passes`` 参数支持丰富的管道描述语法：

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

Legacy PM（可选）仍然使用 ``-load``：

.. code-block:: console

   $ opt -load ./libMyLegacyPass.so -my-pass input.ll -S

调试输出
============

``opt`` 提供了丰富的调试选项：

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

opt 的源码位置
====================

``opt`` 的源码是一个相对较小的文件，展示了如何创建 PassBuilder 和运行 Pass：

`llvm/tools/opt/opt.cpp <file:///home/gzz/creativity/deep_dive_into_llvm/llvm-project/llvm/tools/opt/opt.cpp>`__

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

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
