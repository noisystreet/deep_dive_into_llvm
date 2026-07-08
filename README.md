# 浅入深出 LLVM

LLVM 编译器基础设施的深入分析教程，从入门到源码实现。

## 在线文档

> **https://deep-dive-into-llvm.readthedocs.io**

## 目录结构

```
source/
├── index.rst                  # Sphinx 根文档（toctree 入口）
├── conf.py                    # Sphinx 构建配置
├── volume_01_llvm/            # 第一卷：LLVM
│   ├── preface/               # 前言
│   ├── chapter_01_intro/      # LLVM 简介
│   ├── chapter_02_ir/         # LLVM IR 核心
│   ├── chapter_03_frontend/   # 前端与 Clang
│   ├── chapter_04_pass/       # Pass 框架
│   ├── chapter_05_opt/        # 优化通道
│   ├── chapter_06_tablegen/   # TableGen
│   ├── chapter_07_backend/    # 后端代码生成
│   ├── chapter_08_jit/        # JIT 编译
│   ├── chapter_09_tools/      # LLVM 工具链
│   ├── chapter_10_advanced/   # 进阶与实战
│   └── appendix/              # 附录
└── volume_02_mlir/              # 第二卷：MLIR
    ├── chapter_01_mlir_overview/    # MLIR 概述
    ├── chapter_02_core_concepts/    # 核心概念
    ├── chapter_03_dialects/         # 内置 Dialect
    ├── chapter_04_ods/              # ODS 与 TableGen
    ├── chapter_05_mlir_pass/        # Pass 框架
    ├── chapter_06_lowering/         # Lowering
    ├── chapter_07_mlir_ml_frameworks/  # ML 框架集成
    ├── chapter_08_custom_dialect/   # 自定义 Dialect
    ├── chapter_09_mlir_tools/       # MLIR 工具链
    └── chapter_10_mlir_advanced/    # 进阶主题

examples/                      # 可运行示例代码
llvm-project/                  # LLVM 源码（.gitignore，需单独克隆）
```

## 本地构建

```bash
pip install -r requirements.txt
make html       # 构建 HTML
make serve      # 构建并在 localhost:8000 启动预览
```

## 许可证

[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
