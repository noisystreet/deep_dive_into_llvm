.. _appendix-01-resources:

==========================
参考资源
==========================

本章汇总了学习 LLVM 和 MLIR 过程中最有价值的官方文档、书籍、工具和社区资源。

.. rst-class:: center

   学习 LLVM 的最佳路径：官方文档 + 源码阅读 + 动手实践，三者缺一不可。

官方资源
==================

.. list-table:: LLVM 官方资源
   :header-rows: 1

   * - 资源
     - 地址
     - 说明
   * - 官网
     - `llvm.org <https://llvm.org/>`_
     - LLVM 项目首页
   * - 文档
     - `llvm.org/docs <https://llvm.org/docs/>`_
     - 官方文档集合
   * - Doxygen
     - `llvm.org/doxygen <https://llvm.org/doxygen/>`_
     - API 参考
   * - GitHub
     - `github.com/llvm/llvm-project <https://github.com/llvm/llvm-project>`_
     - 源码仓库
   * - Discourse
     - `discourse.llvm.org <https://discourse.llvm.org/>`_
     - 开发者论坛
   * - Phabricator（归档）
     - `reviews.llvm.org <https://reviews.llvm.org/>`_
     - 代码审查归档
   * - Buildbot
     - `lab.llvm.org/buildbot <https://lab.llvm.org/buildbot/>`_
     - 持续集成

推荐书籍
==================

.. list-table:: LLVM 相关书籍
   :header-rows: 1

   * - 书名
     - 作者
     - 适合读者
   * - *Getting Started with LLVM Core Libraries*
     - Bruno Cardoso Lopes 等
     - 初学者
   * - *LLVM Essentials*
     - Suyog Sarda 等
     - 中级
   * - *Learn LLVM 17*
     - Kai Nacke
     - 中级（最新版）
   * - *Engineering a Compiler*
     - Cooper & Torczon
     - 编译器基础
   * - *Compilers: Principles, Techniques, and Tools* (龙书)
     - Aho, Lam 等
     - 编译器理论

关键官方文档速查
==================

.. list-table:: 必读官方文档
   :header-rows: 1

   * - 文档
     - 内容
     - 对应章节
   * - `LLVM Language Reference Manual <https://llvm.org/docs/LangRef.html>`_
     - LLVM IR 完整参考
     - 第 2 章
   * - `Writing an LLVM Pass <https://llvm.org/docs/WritingAnLLVMNewPMPass.html>`_
     - Pass 编写指南
     - 第 4 章
   * - `TableGen Overview <https://llvm.org/docs/TableGen/index.html>`_
     - TableGen 文档
     - 第 6 章
   * - `CodeGen Architecture <https://llvm.org/docs/CodeGenerator.html>`_
     - 代码生成
     - 第 7 章
   * - `ORC JIT <https://llvm.org/docs/ORCv2.html>`_
     - JIT 编译
     - 第 8 章
   * - `MLIR Documentation <https://mlir.llvm.org/docs/>`_
     - MLIR 官方文档
     - 第二卷全卷

开源项目与工具
==================

**基于 LLVM 的工具和语言** ：

- **Clang** ：C/C++/Objective-C 前端
- **Flang** ：Fortran 前端
- **rustc** （LLVM 后端）：Rust 编译器
- **Julia** （LLVM 后端）：科学计算语言
- **MLIR** ：多级 IR 框架
- **IREE** ：基于 MLIR 的 ML 推理引擎
- **TVM** （LLVM 后端）：深度学习编译器

**开发工具** ：

- **compiler-explorer** （godbolt.org）：在线查看编译器输出
- **llvm-mca** ：LLVM 机器码分析器
- **Performance Analysis Tools** ：perf、Valgrind、XRay

社区资源
==================

- **LLVM Weekly** （llvmweekly.org）：每周 LLVM 新闻摘要
- **MLIR News** ：MLIR 社区动态
- **LLVM Developers' Meeting** ：每年两次的开发者大会
- **EuroLLVM** ：欧洲 LLVM 开发者会议
- **YouTube 频道** ：LLVM 官方演讲和教程
