# 浅入深出 LLVM

LLVM 编译器基础设施的深入分析教程，从入门到源码实现。

## 目录结构

```
source/
├── preface/                   # 前言
├── chapter_01_intro/          # LLVM 简介
├── chapter_02_ir/             # LLVM IR 核心
├── chapter_03_frontend/       # 前端与 Clang
├── chapter_04_pass/           # Pass 框架
├── chapter_05_opt/            # 优化通道
├── chapter_06_tablegen/       # TableGen
├── chapter_07_backend/        # 后端代码生成
├── chapter_08_jit/            # JIT 编译
├── chapter_09_tools/          # LLVM 工具链
├── chapter_10_advanced/       # 进阶与实战
└── appendix/                  # 附录
```

## 本地构建

```bash
pip install -r requirements.txt
make html       # 构建 HTML
make serve      # 构建并在 localhost:8000 启动预览
```

## 许可证

[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
