# agents.md — 浅入深出 LLVM 项目

## 项目概述

本项目编写一本 **浅入深出 LLVM** 技术文档，分为两卷：

- **第一卷：LLVM** — 编译器基础设施（`source/volume_01_llvm/`）
- **第二卷：MLIR** — 多层中间表示（`source/volume_02_mlir/`）

使用 reStructuredText（`.rst`）格式，基于 Sphinx 构建。

- 构建输出：`./_build/html/`（`make html` 后生成）
- 目标读者：有 C/C++ 使用经验、希望了解 LLVM/MLIR 编译器内部机制的开发者
- 参考实现：**LLVM/Clang** 22.x（``llvmorg-22.1.8``）
- 平台：Linux x86_64
- 源码目录：``llvm-project/``（被 ``.gitignore`` 忽略，需要单独克隆）

## LLVM 源码获取

源文件引用依赖 LLVM 源码。在项目根目录下以 ``llvm-project`` 目录名克隆：

.. code-block:: bash

   # 方式一：浅克隆（推荐，节省空间，约 1GB）
   git clone --depth 1 --branch llvmorg-22.1.8 \
       https://github.com/llvm/llvm-project.git llvm-project

   # 方式二：完整克隆（需要全部 git 历史时用，约 15GB）
   git clone --branch llvmorg-22.1.8 \
       https://github.com/llvm/llvm-project.git llvm-project

.. code-block:: bash

   # 切换到已存在的本地 llvm-project 目录中的指定 tag
   cd llvm-project && git fetch --tags && git checkout llvmorg-22.1.8

从源码构建 LLVM（可选，按需执行）：

.. code-block:: bash

   cd llvm-project
   cmake -B build -G Ninja \
       -DCMAKE_BUILD_TYPE=RelWithDebInfo \
       -DLLVM_ENABLE_PROJECTS="clang;lld" \
       -DLLVM_TARGETS_TO_BUILD="X86;AArch64;RISCV" \
       -DLLVM_INCLUDE_TESTS=OFF
   ninja -C build

构建产物（llc, opt, lli 等）位于 ``llvm-project/build/bin/``，可加入 ``PATH``。

## 项目文件说明

| 文件 | 说明 |
|------|------|
| `source/preface/index.rst` | 前言：编写动机、目标读者、预备知识、全书结构 |
| `source/index.rst` | Sphinx 根文档（toctree 入口） |
| `source/chapter_01_intro/` | LLVM 简介（历史、架构概览、Hello World） |
| `source/chapter_02_ir/` | LLVM IR 核心（IR 基础、指令集、元数据、模块结构） |
| `source/chapter_03_frontend/` | 前端与 Clang（AST、CodeGen、Clang 架构） |
| `source/chapter_04_pass/` | LLVM Pass 框架（Pass 基础、分析 Pass、变换 Pass） |
| `source/chapter_05_opt/` | 优化通道（经典优化、内联、循环优化、向量化） |
| `source/chapter_06_tablegen/` | TableGen（DSL 基础、记录、代码生成） |
| `source/chapter_07_backend/` | 后端代码生成（指令选择、寄存器分配、指令调度） |
| `source/chapter_08_jit/` | JIT 编译（MCJIT、ORC JIT、Lazy JIT） |
| `source/chapter_09_tools/` | LLVM 工具链（opt, llc, lli, clang 等工具深度使用） |
| `source/chapter_10_advanced/` | 进阶与实战（LTO、ThinLTO、Sanitizer、调试分析） |
| `source/appendix/` | 附录（参考资源、代码阅读指南、术语表） |
| `source/conf.py` | Sphinx 构建配置 |
| `Makefile` | 构建入口（`make html` / `make clean`） |
| `scripts/precommit-check.sh` | 预提交检查脚本（验证 RST 文档语法） |
| `requirements.txt` | 构建依赖（sphinx, sphinx-rtd-theme, sphinxcontrib-mermaid） |
| `.readthedocs.yaml` | Read the Docs 构建配置 |
| `LICENSE` | CC BY-SA 4.0 许可证 |
| `.gitignore` | 版本控制忽略规则 |
| `agents.md` | **本文件**：AI 助手的工作上下文和约束 |

## 通用约束

1. **许可证**：本文档采用 CC BY-SA 4.0（Creative Commons Attribution-ShareAlike 4.0 International），详见 `LICENSE` 文件
2. **文档格式**：使用 reStructuredText（`.rst`）格式，中文写作
3. **git hooks**：clone 后首次提交前，运行以下命令启用 pre-commit 检查：

   ```bash
   git config --local core.hooksPath .githooks
   ```

   否则 pre-commit 检查不会自动生效。
4. **引用源码**：使用绝对路径的 `file:///` 链接引用源码文件，格式为 `` `链接文本 <file:///绝对路径/文件>`__ ``
5. **避免冗余**：不创建不必要的文件，优先编辑已有文件
6. **代码示例**：在文档中引用代码时，说明其所属文件和行号范围
7. **示例验证**：所有示例代码应保证可编译运行

## 文档写作规范

### 文档结构
- 每篇文档应有标题
- 按章节组织，章节层级不超过三级
- 内容末尾标注生成日期和项目名称

### 引用规范
- 引用源码文件使用绝对路径 markdown 链接
- 引用 API 或概念使用 `` ` `` 反引号标记
- 关键代码片段应提供文件定位

### 内容深度
- 概念讲解与代码示例相结合
- 复杂流程配合 Mermaid 图表说明
- 关键抽象用表格列出其核心字段与方法
- 避免大段堆叠代码，优先提炼核心模式

### 写作风格（核心：浅入深出，夹叙夹议）

**禁止罗列结论**。每一个知识点都必须有推导过程，遵循"是什么 → 为什么 → 怎么用 → 源码长什么样"的递进链条。

- **浅入深出**：从直观可运行的例子出发引入概念，读者能"看见"它在做什么，再逐步揭开底层实现。每一节都遵循：表象问题 → 直观解法 → 引出深层机制 → 源码印证。**不要一上来就甩概念定义或架构图。**
- **夹叙夹议**：叙述"代码做了什么"的同时，必须穿插"为什么这样设计"——性能考量、历史背景、与其他方案的权衡对比。代码是论据，不是结论。
- **避免知识点罗列**：每个新概念必须有上下文铺垫才引入。如果出现"XX有以下几个特点：1... 2... 3..."这种列表体，必须有前置案例让读者自然感受到这些特点的存在，而不是突兀地堆砌。
- **代码即证据**：每一个论断必须附代码或源码引用佐证。没有源码引用支撑的观点都是空谈。关键代码片段要标注来自 LLVM 源码的具体文件和行号。
- **过渡自然**：段落之间、章节之间要有承上启下的过渡句。比如"上一节我们看到了 X 的行为，但它背后依赖 Y 机制，接下来我们深入 Y"。禁止生硬切换话题。

## 写作路线图

按以下顺序推进内容编写：

1. **第 1 章：LLVM 简介** — LLVM 历史、架构概览、Hello World、基本工具使用
2. **第 2 章：LLVM IR 核心** — IR 基础语法、指令集、元数据、Module/Function/BasicBlock 结构
3. **第 3 章：前端与 Clang** — Clang 架构、AST、代码生成流程、Clang 编译过程
4. **第 4 章：LLVM Pass 框架** — Legacy Pass Manager、New PM、分析 Pass、变换 Pass
5. **第 5 章：优化通道** — 函数内联、循环优化、常量传播、向量化、IPO
6. **第 6 章：TableGen** — TableGen 语言基础、Record、Class、DAG、代码生成
7. **第 7 章：后端代码生成** — 指令选择（SelectionDAG）、寄存器分配、指令调度、MC 层
8. **第 8 章：JIT 编译** — MCJIT、ORC JIT 架构、Lazy Compilation、LLJIT
9. **第 9 章：LLVM 工具链** — opt、llc、lli、llvm-dis、llvm-as、FileCheck 等工具的深度使用
10. **第 10 章：进阶与实战** — LTO/ThinLTO、Sanitizer、LLVM 调试、性能分析、自定义后端

## 构建方法

```bash
# 安装依赖
pip install -r requirements.txt

# 构建 HTML 文档
make html

# 构建产物位于 _build/html/
```

自动部署到 Read the Docs 后，文档会自动构建并托管。本地构建也可通过 `make html` 完成。

## Cursor Cloud specific instructions

本项目是一个 **Sphinx 文档站点**（中文 LLVM 教程），"运行应用"即构建并预览 HTML 文档。依赖已由启动 update script (`pip install -r requirements.txt`) 安装好（`sphinx` / `sphinx-rtd-theme` / `sphinxcontrib-mermaid`）。常用命令见 `README.md` 与 `Makefile`，下面只记录非显而易见的注意事项：

- **构建**：`make html`（产物在 `_build/html/`）。本地开发用 `make html` 即可；不要加 `-W`。CI（`.github/workflows/ci.yml`）使用 `make html SPHINXOPTS="-W"` 把警告当错误。
- **预览**：`make serve` 会先构建再用 `python3 -m http.server` 启动预览，默认端口 8000（`PORT` 变量未设时为 8000）。也可直接 `cd _build/html && python3 -m http.server 8000`。
- **Lint / RST 检查**：`bash scripts/precommit-check.sh`（即 CI 的 "Check RST syntax" 步骤）。脚本会运行 Sphinx 语法解析；内联标记风格（如 `**bold**` 后紧跟中文标点）仅作提示，不阻塞 CI。
- **git hooks**（仅在需要提交触发 pre-commit RST 检查时）：`git config --local core.hooksPath .githooks`。
- 修改 `.rst` 内容后无热重载，需重新 `make html` 才能在预览中看到更新。
