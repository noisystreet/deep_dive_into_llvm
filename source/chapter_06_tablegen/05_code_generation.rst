.. _chapter-06-05-code-generation:

==========================
TableGen 代码生成
==========================

前几节看到的都是 TableGen 的"语言"部分——如何编写 ``.td`` 文件。
本节我们来看"编译器"部分：``llvm-tblgen`` 如何消费 ``.td`` 文件并生成 C++ 代码。

.. rst-class:: center

   TableGen 的"编译器"只做一件事：**解析 .td 文件，生成 Record 的集合，
   然后转交给 C++ 后端（Backend）来输出代码**。

llvm-tblgen 的架构
======================

``llvm-tblgen`` 的内部架构分为两层：

.. mermaid::

   flowchart TD
       subgraph 前端（前端）
           A[.td 文件] --> B[词法/语法分析]
           B --> C[Record 数据库]
       end
       subgraph 后端（后端）
           C --> D1[-gen-instr-info]
           C --> D2[-gen-register-info]
           C --> D3[-gen-dag-isel]
           C --> D4[-gen-asm-writer]
           C --> D5[-gen-subtarget]
           C --> D6[自定义后端...]
       end

       style A fill:#ff9800,color:#fff
       style C fill:#4a9eff,color:#fff

**前端：** 解析 ``.td`` 文件，构建 Record 数据库。所有 ``.td`` 文件被展开为
一组 ``Record`` 对象。

**后端：** 遍历 Record 数据库，根据后端类型生成不同的输出。每种后端对应
一个 C++ 类，继承自 ``TableGenBackend``。

内置后端详解
=================

TableGen 内置了多个后端，每个生成一种 ``*Gen*.inc`` 文件。

**1. -gen-register-info（寄存器信息）**

生成寄存器枚举、寄存器类、寄存器别名等。

.. code-block:: console

   $ llvm-tblgen -gen-register-info X86.td -o X86GenRegisterInfo.inc

生成的 C++ 代码示例：

.. code-block:: cpp

   // 由 TableGen 自动生成
   enum Registers {
       RAX = 0,
       RBX = 1,
       RCX = 2,
       // ...
   };

**2. -gen-instr-info（指令信息）**

生成指令枚举、指令属性、操作数类型等。

.. code-block:: console

   $ llvm-tblgen -gen-instr-info X86InstrInfo.td -o X86GenInstrInfo.inc

生成的 C++ 代码包含数万行指令枚举定义：

.. code-block:: cpp

   enum {
       ADD32rr = 0,
       ADD32rm = 1,
       SUB32rr = 2,
       // ... 成百上千条指令
   };

**3. -gen-dag-isel（DAG 指令选择）**

这是**最复杂**的 TableGen 后端。它将 ``.td`` 中的 Pattern 编译为一个高效的
匹配表（通常包含数万行 switch-case 代码）：

.. code-block:: cpp

   // 生成的匹配表（简化）
   SDNode *SelectCode(SDNode *N) {
       switch (N->getOpcode()) {
       case ISD::ADD: {
           // 尝试匹配 ADD32rr
           if (N->getOperand(0)->getOpcode() == ISD::Register &&
               N->getOperand(1)->getOpcode() == ISD::Register) {
               return CurDAG->getMachineNode(X86::ADD32rr, DL, ...);
           }
           break;
       }
       // ...
       }
   }

**4. -gen-asm-writer（汇编输出）**

生成将指令对象转换为汇编文本的代码：

.. code-block:: cpp

   // 生成的汇编打印函数
   void X86InstPrinter::printInstruction(const MCInst *MI) {
       switch (MI->getOpcode()) {
       case X86::ADD32rr:
           AsmWriter << "add\t" << MI->getOperand(0) << ", "
                     << MI->getOperand(1);
           break;
       // ...
       }
   }

**5. -gen-asm-matcher（汇编匹配）**

生成将汇编文本匹配为指令对象的代码——汇编器的核心：

.. code-block:: cpp

   // 生成的汇编匹配函数
   MatchResult MatchInstruction(StringRef Asm) {
       // 用生成的匹配表将 "add %eax, %ebx" → ADD32rr
   }

**6. -gen-subtarget（处理器特性）**

生成处理器特性（feature）和调度模型的枚举：

.. code-block:: cpp

   enum {
       FeatureSSE1,
       FeatureSSE2,
       FeatureAVX,
       FeatureAVX512,
       // ...
   };

自定义 TableGen 后端
============================

你也可以编写自己的 TableGen 后端。步骤是：

1. 创建一个 C++ 类，继承 ``TableGenBackend``
2. 实现 ``run`` 方法，遍历 Record 数据库
3. 注册到 ``llvm-tblgen`` 中

.. code-block:: cpp

   #include "llvm/TableGen/TableGenBackend.h"

   class MyBackend : public TableGenBackend {
   public:
       MyBackend(RecordKeeper &Records) : TableGenBackend(Records) {}

       void run(raw_ostream &OS) override {
           // 遍历所有 Instruction 类型的 Record
           auto Instrs = Records.getAllDerivedDefinitions("Instruction");
           for (auto *I : Instrs) {
               OS << "Instruction: " << I->getName() << "\n";
               // 获取字段值
               OS << "  Mnemonic: " << I->getValueAsString("Mnemonic") << "\n";
           }
       }
   };

   // 注册到 tblgen
   static TableGen::RegisterBackend<MyBackend>
       X("my-backend", "Generate my custom output");

然后在构建系统中添加：

.. code-block:: cmake

   # CMakeLists.txt
   set(LLVM_TABLEGEN_PROJECT "MyBackend")
   add_tablegen(MyTblGen my-tblgen ...)

TableGen 源码架构
======================

.. code-block:: text

   llvm/utils/TableGen/
   ├── TableGen.cpp               # llvm-tblgen 入口
   ├── Record.h / Record.cpp      # Record 数据类型
   ├── TGLexer.h / TGLexer.cpp    # 词法分析器
   ├── TGParser.h / TGParser.cpp  # 语法分析器
   ├── TGStarter.cpp              # 启动后端
   ├── RegisterInfoEmitter.cpp    # -gen-register-info 后端
   ├── InstrInfoEmitter.cpp       # -gen-instr-info 后端
   ├── DAGISelEmitter.cpp         # -gen-dag-isel 后端
   ├── AsmWriterEmitter.cpp       # -gen-asm-writer 后端
   ├── AsmMatcherEmitter.cpp      # -gen-asm-matcher 后端
   ├── SubtargetEmitter.cpp       # -gen-subtarget 后端
   └── ...

每个 ``*Emitter.cpp`` 对应一个 TableGen 后端，读取 Record 数据库并输出 C++ 代码。
这些后端的源码本身是学习"如何遍历 Record"的最佳教材。

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
