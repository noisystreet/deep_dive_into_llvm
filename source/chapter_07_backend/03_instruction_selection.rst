.. _chapter-07-03-instruction-selection:

==========================
指令选择
==========================

.. TODO: 本节内容

    - SelectionDAG 指令选择的流程
    - Pattern Matching：如何用 TableGen 描述指令模式
    - 复杂模式的匹配与分裂
    - FastISel：快速但有限的指令选择
    - GlobalISel 概述：与 SelectionDAG 的对比
    - GlobalISel 的流水线：IR → MIR → Generic Opcodes → Legalize → Combine → Select
