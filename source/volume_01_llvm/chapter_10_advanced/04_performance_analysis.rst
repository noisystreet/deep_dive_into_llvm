.. _chapter-10-04-performance-analysis:

======================
性能分析
======================

LLVM 编译器本身也是一个性能敏感的程序。随着代码库增长，编译时间会成为
开发效率的瓶颈。LLVM 提供了多种工具来分析编译性能。

.. rst-class:: center

   优化 LLVM 的编译时间比优化 LLVM 生成的代码同样重要——
   毕竟编译器本身也需要快速运行。

编译时间分析：-time-passes
=================================

``opt`` 和 ``llc`` 都支持 ``-time-passes`` 选项，显示每个 Pass 的耗时：

.. code-block:: console

   $ opt -passes='default<O2>' -time-passes input.ll -S -o /dev/null

   ===-------------------------------------------------------------------------===
                           LLVM Pass Execution Timing Report
   ===-------------------------------------------------------------------------===
     Total Execution Time: 0.3456 seconds

      ---User Time---   --System Time--   --User+System--   ---Wall Time---
      0.2868 ( 83.0%)   0.0156 ( 80.3%)   0.3024 ( 83.0%)   0.3024 ( 83.0%)  InlinerPass
      0.0288 (  8.3%)   0.0012 (  6.2%)   0.0300 (  8.2%)   0.0300 (  8.2%)  GVN
      0.0120 (  3.5%)   0.0012 (  6.2%)   0.0132 (  3.6%)   0.0132 (  3.6%)  InstCombine
      0.0084 (  2.4%)   0.0000 (  0.0%)   0.0084 (  2.3%)   0.0084 (  2.3%)  LoopSimplify
      0.0048 (  1.4%)   0.0000 (  0.0%)   0.0048 (  1.3%)   0.0048 (  1.3%)  SimplifyCFG
      ...

这个报告能告诉你： **内联 Pass 占了 83% 的编译时间** 。

使用 ``-time-passes`` 的几个实用场景：

.. code-block:: console

   # 对比不同优化等级的编译时间
   $ opt -passes='default<O1>' -time-passes input.ll -S -o /dev/null
   $ opt -passes='default<O2>' -time-passes input.ll -S -o /dev/null
   $ opt -passes='default<O3>' -time-passes input.ll -S -o /dev/null

   # 分析后端各环节的时间
   $ llc -time-passes input.ll -o /dev/null

   # 将报告输出到文件
   $ opt -passes='default<O2>' -time-passes input.ll -o output.bc \
         2> time_report.txt

Pass 统计信息：-stats
==============================

``-stats`` 显示每个 Pass 执行的统计计数：

.. code-block:: console

   $ opt -passes='mem2reg,instcombine,gvn' -stats input.ll -S -o /dev/null
   3 instcombine - Number of dead inst eliminated
   2 gvn - Number of instructions deleted
   1 gvn - Number of redundant loads eliminated

这些统计信息在调试 Pass 行为时非常有用——你可以验证 Pass 是否如预期工作，
或者对比两个版本的 Pass 哪个更有效。

使用 perf 分析 LLVM 的性能
====================================

对于更细粒度的性能分析，使用 ``perf`` ：

.. code-block:: console

   # 分析编译过程中的热点函数
   $ perf record -g -- opt -passes='default<O2>' input.ll -S -o /dev/null
   $ perf report

   # 分析内存分配
   $ perf stat -e cache-misses,branch-misses opt ...

   # 分析调用图
   $ perf record -F 99 -g -- clang -O2 hello.c -c -o hello.o
   $ perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg

编译时间 vs. 运行时间的权衡
===================================

优化编译器本质上是一个 **投资回报** 问题：编译时间投入越多，生成的代码通常越快。
但边际收益递减。

.. list-table:: 优化等级与时间权衡
   :header-rows: 1

   * - 优化等级
     - 编译时间（相对）
     - 运行时间（相对）
     - 适用场景
   * - -O0
     - 1x
     - 10x~50x
     - 调试、开发
   * - -O1
     - 2x~3x
     - 3x~5x
     - 少量优化
   * - -O2
     - 5x~10x
     - 1.5x~2x
     - 默认发布
   * - -O3
     - 10x~15x
     - 1x~1.2x
     - 计算密集
   * - -Os
     - 5x~10x
     - 2x~4x（体积优化）
     - 嵌入式

使用 CMake 的 LLVM_BUILD_BENCHMARKS
==========================================

如果你想在自己的机器上运行 LLVM 的基准测试套件：

.. code-block:: console

   $ cmake -B build \
       -DLLVM_BUILD_BENCHMARKS=ON \
       -DLLVM_ENABLE_PROJECTS="clang;lld" \
       -DCMAKE_BUILD_TYPE=Release
   $ ninja -C build
   $ cd build/benchmarks
   $ python3 run.py

这个套件包含多个 micro-benchmark，可以衡量不同 LLVM 版本之间的编译速度变化。

编译速度优化技巧
======================

**1. 使用 LLD 代替 GNU ld**

.. code-block:: console

   $ cmake -DLLVM_USE_LINKER=lld ...

**2. 使用 Ninja 代替 Make**

.. code-block:: console

   $ cmake -G Ninja ...

**3. 只构建需要的目标架构**

.. code-block:: console

   $ cmake -DLLVM_TARGETS_TO_BUILD="X86;AArch64" ...

**4. 使用 ThinLTO 优化编译时间**

.. code-block:: console

   $ cmake -DLLVM_ENABLE_LTO=Thin ...

**5. 启用模块化构建**

.. code-block:: console

   $ cmake -DLLVM_ENABLE_MODULES=ON ...
