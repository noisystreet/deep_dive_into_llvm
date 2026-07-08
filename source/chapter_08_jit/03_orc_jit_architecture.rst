.. _chapter-08-03-orc-jit-architecture:

==========================
ORC JIT 架构
==========================

.. TODO: 本节内容

    - ORC JIT 的设计哲学：分层与异步
    - 核心抽象：ExecutionSession、JITDylib、Layer、MaterializationUnit
    - JITDylib 与符号解析
    - Layer 的职责与堆叠
    - IRTransformLayer、ObjectLinkingLayer、CompileOnDemandLayer
    - Materialization 过程详解
    - 异步编译的支持机制
