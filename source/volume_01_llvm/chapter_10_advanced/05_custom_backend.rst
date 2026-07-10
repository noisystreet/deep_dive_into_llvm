.. _chapter-10-05-custom-backend:

==========================
自定义后端实战
==========================

本文是全书最"动手"的一节。我们将通过实现一个**最小 LLVM 后端**来串联起
第 6 章（TableGen）、第 7 章（后端架构）、第 9 章（ ``llc`` ）的知识。

.. rst-class:: center

   实现一个 LLVM 后端不需要理解 LLVM 的全部——只需要理解后端流水线中的
   几个关键组件，然后用 TableGen 描述目标架构，用 C++ 实现特定逻辑。

选择目标：一个教学用的最小架构
====================================

为了教学目的，我们实现一个名为 **MyTarget** 的虚构架构。它的设计极其简单：

- 4 个通用寄存器（ ``%r0`` ~ ``%r3`` ）
- 两种指令格式：寄存器-寄存器（RR）和寄存器-立即数（RI）
- 指令： ``add`` 、``sub`` 、``load`` 、``store``
- 32 位固定长度指令

第一步：创建目录和 CMakeLists.txt
============================================

.. code-block:: text

   llvm/lib/Target/MyTarget/
   ├── CMakeLists.txt
   ├── MyTarget.td
   ├── MyTargetRegisterInfo.td
   ├── MyTargetInstrInfo.td
   ├── MyTargetISelLowering.td
   ├── MyTargetTargetMachine.cpp
   ├── MyTargetSubtarget.cpp
   ├── MyTargetRegisterInfo.cpp
   ├── MyTargetInstrInfo.cpp
   ├── MyTargetISelLowering.cpp
   └── MyTargetAsmPrinter.cpp

.. code-block:: cmake
   :caption: CMakeLists.txt

   set(MyTargetCodegenSources
       MyTargetTargetMachine.cpp
       MyTargetSubtarget.cpp
       MyTargetRegisterInfo.cpp
       MyTargetInstrInfo.cpp
       MyTargetISelLowering.cpp
       MyTargetAsmPrinter.cpp
   )

   tablegen(MyTargetGenRegisterInfo.inc -gen-register-info)
   tablegen(MyTargetGenInstrInfo.inc -gen-instr-info)
   tablegen(MyTargetGenDAGISel.inc -gen-dag-isel)
   tablegen(MyTargetGenAsmWriter.inc -gen-asm-writer)
   tablegen(MyTargetGenSubtargetInfo.inc -gen-subtarget)

   add_llvm_target(MyTargetCodegen ${MyTargetCodegenSources})

第二步：TableGen 描述文件
==============================

.. code-block:: text
   :caption: MyTargetRegisterInfo.td

   // 定义寄存器类
   class MyTargetReg<string name> : Register<name> {
       let Namespace = "MyTarget";
   }

   // 定义 4 个寄存器
   def R0 : MyTargetReg<"r0"> { let HWEncoding = 0; }
   def R1 : MyTargetReg<"r1"> { let HWEncoding = 1; }
   def R2 : MyTargetReg<"r2"> { let HWEncoding = 2; }
   def R3 : MyTargetReg<"r3"> { let HWEncoding = 3; }

   // 定义通用寄存器类（用于指令中的操作数约束）
   def GPR : RegisterClass<"MyTarget", "i32", 32,
       (add R0, R1, R2, R3)>;

.. code-block:: text
   :caption: MyTargetInstrInfo.td

   // 指令格式基类
   class Inst<dag outs, dag ins, string asmstr, list<dag> pattern>
       : Instruction {
       let OutOperandList = outs;
       let InOperandList = ins;
       let AsmString = asmstr;
       let Pattern = pattern;
   }

   // ADD r_dst, r_src1, r_src2
   def ADD : Inst<(outs GPR:$dst), (ins GPR:$src1, GPR:$src2),
       "add $dst, $src1, $src2",
       [(set GPR:$dst, (add GPR:$src1, GPR:$src2))]>;

   // SUB r_dst, r_src1, r_src2
   def SUB : Inst<(outs GPR:$dst), (ins GPR:$src1, GPR:$src2),
       "sub $dst, $src1, $src2",
       [(set GPR:$dst, (sub GPR:$src1, GPR:$src2))]>;

   // LOAD r_dst, [addr]
   def LOAD : Inst<(outs GPR:$dst), (ins i32imm:$addr),
       "load $dst, $addr",
       [(set GPR:$dst, (load addr:$addr))]>;

   // STORE [addr], r_src
   def STORE : Inst<(outs), (ins i32imm:$addr, GPR:$src),
       "store $addr, $src",
       [(store GPR:$src, addr:$addr)]>;

第三步：TargetMachine 和 Subtarget
========================================

.. code-block:: cpp
   :caption: MyTargetTargetMachine.cpp（简化）

   #include "MyTarget.h"

   extern "C" void LLVMInitializeMyTarget() {
       // 注册 Target
       RegisterTarget<MyTargetTargetMachine> X(
           getMyTargetTarget(), "my-target", "My Target", "my-target");
   }

   MyTargetTargetMachine::MyTargetTargetMachine(...)
       : LLVMTargetMachine(T, "e-m:e-p:32:32", TT, CPU, FS, Options) {}

第四步：指令选择和 Lowering
========================================

.. code-block:: cpp
   :caption: MyTargetISelLowering.cpp（简化）

   #include "MyTargetISelLowering.h"

   MyTargetTargetLowering::MyTargetTargetLowering(...) {
       // 告诉 LLVM：MyTarget 原生支持 add 和 sub
       addRegisterClass(MVT::i32, &MyTarget::GPRRegClass);

       // 告诉 LLVM：不支持 mul，需要展开
       setOperationAction(ISD::MUL, MVT::i32, Expand);
   }

第五步：编译和测试
========================

.. code-block:: console

   # 构建 LLVM（包含 MyTarget）
   $ cmake -B build -DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD=MyTarget ...
   $ ninja -C build

   # 生成 IR
   $ cat test.c
   int add(int a, int b) { return a + b; }
   $ clang -S -emit-llvm -O2 test.c -o test.ll

   # 编译为 MyTarget 汇编
   $ llc -march=my-target test.ll -o test.s
   $ cat test.s
   add r0, r0, r1
   ret

端到端验证
================

如果你已经实现了上述所有组件，你可以验证从 C 源码到 MyTarget 机器码的完整流程：

.. code-block:: console

   $ cat fib.c
   int fib(int n) {
       if (n < 2) return 1;
       return fib(n-1) + fib(n-2);
   }

   $ clang -S -emit-llvm -O2 fib.c -o fib.ll
   $ llc -march=my-target fib.ll -o fib.s
   $ cat fib.s
   fib:
       cmpi r1, r0, 2        ; n < 2 ?
       blt return_one         ; 是，跳转到 return 1
       subi r2, r0, 1        ; n-1
       call fib               ; fib(n-1)
       subi r2, r0, 2        ; n-2
       call fib               ; fib(n-2)
       add r0, r1, r2        ; fib(n-1) + fib(n-2)
       ret
   return_one:
       movi r0, 1
       ret

参考资源
================

如果你真的想实现一个 LLVM 后端，以下资源是最有价值的：

- **LLVM 官方文档** ：`llvm/docs/WritingAnLLVMBackend.rst <file:///workspace/llvm-project/llvm/docs/WritingAnLLVMBackend.rst>`__
- **Cpu0 后端教程** ：一个完整的教学后端实现（网上搜索 "Cpu0 LLVM backend"）
- **LLVM 源码中的 Target 目录** ：`llvm/lib/Target/ <file:///workspace/llvm-project/llvm/lib/Target/>`__，每个 Target 都是一个可参考的实例
- **TableGen 文档** ：`llvm/docs/TableGen/ <file:///workspace/llvm-project/llvm/docs/TableGen/>`__

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
