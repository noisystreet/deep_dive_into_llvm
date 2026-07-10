.. _appendix-04-environment:

==========================
环境说明
==========================

本章介绍如何搭建 LLVM/MLIR 开发环境，包括从源码编译 LLVM、常用 CMake 配置、
Docker 镜像以及 LLVM 版本选择建议。

.. rst-class:: center

   推荐配置：Ubuntu 22.04 + LLVM 17/18 + Ninja + ccache，
   可以在 15 分钟内完成首次构建。

操作系统与工具链
======================

**支持的操作系统** ：

- **Linux** （推荐 Ubuntu 22.04+、Fedora 38+、Debian 12+）
- **macOS** （13+，需 Xcode 或 Command Line Tools）
- **Windows** （Visual Studio 2022，实验性支持）

**前置依赖** （Ubuntu/Debian）：

.. code-block:: console

   $ sudo apt install build-essential cmake ninja-build \
       git python3 ccache curl

从源码编译 LLVM
======================

.. code-block:: console

   # 1. 克隆仓库
   $ git clone --depth=1 -b llvmorg-18.1.0 \
       https://github.com/llvm/llvm-project.git
   $ cd llvm-project

   # 2. 创建构建目录
   $ mkdir build && cd build

   # 3. 配置
   $ cmake -G Ninja ../llvm \
       -DCMAKE_BUILD_TYPE=Release \
       -DLLVM_ENABLE_PROJECTS="clang;lld" \
       -DLLVM_ENABLE_RUNTIMES="compiler-rt" \
       -DLLVM_TARGETS_TO_BUILD="X86;AArch64;RISCV" \
       -DLLVM_CCACHE_BUILD=ON \
       -DCMAKE_INSTALL_PREFIX=/usr/local/llvm-18

   # 4. 构建（使用所有 CPU 核心）
   $ ninja -j$(nproc)

   # 5. 安装
   $ sudo ninja install

**CMake 选项说明** ：

.. list-table:: 常用 CMake 选项
   :header-rows: 1

   * - 选项
     - 可选值
     - 说明
   * - ``CMAKE_BUILD_TYPE``
     - ``Release`` / ``Debug`` / ``RelWithDebInfo``
     - 构建类型
   * - ``LLVM_ENABLE_PROJECTS``
     - ``clang;lld;mlir``
     - 启用的子项目
   * - ``LLVM_TARGETS_TO_BUILD``
     - ``X86;AArch64;RISCV``
     - 目标架构
   * - ``LLVM_CCACHE_BUILD``
     - ``ON`` / ``OFF``
     - 启用 ccache 加速
   * - ``LLVM_PARALLEL_LINK_JOBS``
     - ``4``
     - 并行链接任务数
   * - ``LLVM_BUILD_LLVM_DYLIB``
     - ``ON`` / ``OFF``
     - 构建动态库
   * - ``LLVM_ENABLE_ASSERTIONS``
     - ``ON`` / ``OFF``
     - 启用断言（Debug 默认 ON）

启用 MLIR 构建
======================

如果需要构建 MLIR：

.. code-block:: console

   $ cmake -G Ninja ../llvm \
       -DLLVM_ENABLE_PROJECTS="mlir;clang" \
       -DLLVM_TARGETS_TO_BUILD="X86" \
       -DLLVM_CCACHE_BUILD=ON \
       -DCMAKE_BUILD_TYPE=Release

   $ ninja -j$(nproc) check-mlir

使用 ccache 加速
======================

LLVM 的首次完整构建可能需要 30-60 分钟。ccache 可以将后续增量构建
时间缩短到几分钟：

.. code-block:: console

   $ sudo apt install ccache
   $ ccache -M 50G            # 设置缓存上限
   $ cmake ... -DLLVM_CCACHE_BUILD=ON

**ccache 命中率检查** ：

.. code-block:: console

   $ ccache -s

推荐的 LLVM 版本
======================

.. list-table:: LLVM 版本选择
   :header-rows: 1

   * - 版本
     - 状态
     - 适用场景
   * - LLVM 18
     - 最新稳定版
     - 新项目推荐
   * - LLVM 17
     - 稳定版
     - 生产环境
   * - LLVM 16
     - 旧稳定版
     - 兼容已有项目
   * - Main
     - 开发版
     - 贡献者/尝鲜

快速安装（预编译包）
========================

**Ubuntu（apt.llvm.org）** ：

.. code-block:: console

   $ wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -
   $ sudo add-apt-repository "deb https://apt.llvm.org/$(lsb_release -sc)/ llvm-toolchain-$(lsb_release -sc)-18 main"
   $ sudo apt update && sudo apt install clang-18 lld-18 libclang-18-dev

**macOS（Homebrew）** ：

.. code-block:: console

   $ brew install llvm
   $ echo 'export PATH="/opt/homebrew/opt/llvm/bin:$PATH"' >> ~/.zshrc

Docker 开发环境
======================

使用官方 Docker 镜像快速搭建环境：

.. code-block:: console

   # 官方开发镜像
   $ docker pull ghcr.io/llvm/llvm-project/llvm-project:latest

   # 或者使用自定义 Dockerfile
   $ cat > Dockerfile << 'EOF'
   FROM ubuntu:22.04
   RUN apt update && apt install -y build-essential cmake ninja-build \
       git python3 ccache clang
   WORKDIR /workspace
   EOF

验证安装
==============

.. code-block:: console

   $ clang --version
   $ opt --version
   $ llc --version

   # 验证 MLIR（如果构建了 MLIR）
   $ mlir-opt --version
   $ mlir-translate --version

   # 测试一个简单的 LLVM IR 程序
   $ echo 'define i32 @main() { ret i32 42 }' | llc -filetype=obj -o /dev/null
   $ echo '✅ LLVM 工作正常'

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
