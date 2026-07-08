.. _chapter-10-01-lto:

==========================
链接时优化（LTO）
==========================

链接时优化（Link-Time Optimization, LTO）是**跨越编译单元边界的优化**。
它将优化从"每个源文件独立进行"扩展到"整个程序可见"。

.. rst-class:: center

   没有 LTO 时，优化器被局限在单个翻译单元内，像戴着眼罩工作。
   LTO 摘掉了眼罩。

为什么需要 LTO？
====================

假设你有两个源文件：

.. code-block:: c

   // foo.c
   int add(int a, int b) { return a + b; }

   // bar.c
   int main() {
       return add(1, 2);
   }

单独编译时（ ``-O2`` ），编译器只能分别优化 ``foo.c`` 和 ``bar.c``：

- 编译 ``foo.c`` 时：编译器不知道 ``add`` 只有 ``main`` 一个调用点
- 编译 ``bar.c`` 时：编译器看不到 ``add`` 的函数体，无法内联

所以生成的代码会包含实际的 ``call add`` 指令，而不是直接内联计算结果。

LTO 的做法是：将 IR 的优化推迟到链接阶段，让链接器"看到"所有翻译单元的 IR。

LTO 的工作流程
===================

.. mermaid::

   flowchart LR
       subgraph 编译阶段
           A[foo.c] --> A1[clang -flto]
           B[bar.c] --> B1[clang -flto]
           A1 --> A2[foo.bc]
           B1 --> B2[bar.bc]
       end
       subgraph 链接阶段
           A2 --> C["链接器（ld.lld）"]
           B2 --> C
           C --> D["LLVM 优化\n（整个程序可见）"]
           D --> E["目标代码"]
       end

       style D fill:#ff9800,color:#fff

1. **编译阶段**：使用 ``-flto`` 编译时，clang 生成 LLVM 比特码（ ``.bc`` ）代替目标文件（ ``.o`` ）
2. **链接阶段**：链接器（如 ``lld`` ）检测到输入文件是比特码，调用 LLVM 的 LTO 插件
3. **全程序优化**：LTO 插件将所有比特码合并到一个 Module 中，运行跨模块的优化 Pass
4. **代码生成**：优化完成后，生成最终的目标代码

使用方式：

.. code-block:: console

   # 开启 Full LTO
   $ clang -flto -O2 foo.c bar.c -o a.out

   # 开启 ThinLTO
   $ clang -flto=thin -O2 foo.c bar.c -o a.out

Full LTO vs ThinLTO
==========================

Full LTO 虽然优化效果好，但有一个严重问题：**合并所有 IR 会消耗大量内存和时间**。
对于一个包含数千个源文件的项目，Full LTO 可能需要数十 GB 内存和数十分钟链接时间。

**ThinLTO** 的设计解决了这个问题。它的核心思想在前面第 5.6 节已经介绍过，
这里从应用角度做对比：

.. list-table:: Full LTO vs ThinLTO
   :header-rows: 1

   * - 特征
     - Full LTO
     - ThinLTO
   * - IR 处理
     - 合并所有 IR 到一个 Module
     - 保持 IR 分离，只合并摘要
   * - 内存消耗
     - 高（O(总 IR 大小)）
     - 低（O(摘要大小)）
   * - 链接时间
     - 慢（串行处理）
     - 快（并行后端）
   * - 优化质量
     - 最佳
     - 接近 Full LTO
   * - 构建系统集成
     - 简单（替换链接器）
     - 需要额外索引步骤

Clang 中启用 ThinLTO：

.. code-block:: console

   # 编译 + 链接，一步完成
   $ clang -flto=thin -O2 *.c -o program

   # 分步构建
   $ clang -flto=thin -O2 -c foo.c -o foo.o   # 生成 .o（内含 IR）
   $ clang -flto=thin -O2 -c bar.c -o bar.o
   $ clang -flto=thin foo.o bar.o -o program   # 链接时触发 LTO

查看 ThinLTO 的索引步骤：

.. code-block:: console

   $ clang -flto=thin -O2 foo.c bar.c -o program -Wl,-save-temps

这会生成中间文件供你检查 LTO 的处理过程。

LTO 与 Device Linkage
==========================

有些项目需要处理"设备代码"和"主机代码"的分离（如 GPU 编程）。
LLVM 的 LTO 框架通过 **Device Linkage** 支持这种场景：

.. code-block:: cpp

   // 标记设备函数
   __attribute__((device)) int kernel(...) { ... }

LTO 插件会识别设备函数，在主机代码的 LTO 过程中排除它们，
保持设备函数的独立编译路径。

在 CMake 中启用 LTO
=========================

.. code-block:: cmake

   # 项目级别的 LTO 配置
   set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)

   # 或指定 ThinLTO
   set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_THIN TRUE)

   # 针对特定目标
   set_target_properties(my_target PROPERTIES
       INTERPROCEDURAL_OPTIMIZATION TRUE)

LTO 对二进制大小和性能的影响
==================================

根据 LLVM 社区的基准测试，ThinLTO 在大项目（如 Chromium、Firefox、Clang 自身）
上的典型收益：

- **运行时间**：减少 5%~15%（得益于跨模块内联和常量传播）
- **二进制大小**：减少 3%~8%（得益于死代码消除）
- **链接时间**：比 Full LTO 快 3~5 倍
- **编译时间**：不变（编译阶段不增加时间）

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
