.. _chapter-07-07-target-description:

==========================
Target 描述与注册
==========================

LLVM 支持数十种目标架构（X86、AArch64、ARM、RISCV、AMDGPU 等）。每个目标
架构的实现都遵循一个统一的框架，通过 **Target 注册机制** 集成到 LLVM 中。

.. rst-class:: center

   添加一个新的目标架构到 LLVM，就是在注册表中注册一组工厂函数，
   让 LLVM 知道如何为这个架构创建后端组件。

Triple：目标三元组
======================

目标架构由 **Triple** （目标三元组）标识。Triple 的格式是：

.. code-block:: text

   <arch>-<vendor>-<os>-<environment>

   x86_64-unknown-linux-gnu      # x86_64 Linux
   aarch64-apple-darwin22        # Apple Silicon macOS 13
   riscv64-unknown-linux-gnu     # RISC-V 64 Linux
   wasm32-unknown-wasi           # WebAssembly WASI

LLVM 中使用 ``Triple`` 类来解析和操作它：

.. code-block:: text

   Triple T("x86_64-unknown-linux-gnu");
   T.getArch()     → Triple::x86_64
   T.getOS()       → Triple::Linux
   T.getVendor()   → Triple::UnknownVendor
   T.isArch64Bit() → true

TargetRegistry：目标注册表
===============================

``TargetRegistry`` 是 LLVM 的"目标架构目录"。每个目标后端在初始化时向
这个注册表注册自己：

.. code-block:: cpp

   // 注册 X86 目标
   static Target TheX86Target;
   extern "C" void LLVMInitializeX86TargetInfo() {
       RegisterTarget X(TheX86Target, "x86", "X86", "X86-32",
                        Target::getAttrs()...);
   }

   // 注册 X86-64 子目标
   static Target TheX86_64Target;
   extern "C" void LLVMInitializeX86TargetInfo() {
       RegisterTarget X(TheX86_64Target, "x86-64", "X86", "X86-64",
                        Target::getAttrs()...);
   }

初始化函数通过 LLVM 的初始化机制自动调用：

.. code-block:: cpp

   // 在代码中初始化所有启用目标
   LLVMInitializeAllTargets();      // 初始化所有目标
   LLVMInitializeX86Target();       // 只初始化 X86
   LLVMInitializeAArch64Target();   // 只初始化 AArch64

注册的组件
================

每个目标架构注册以下组件：

.. list-table:: 目标架构注册的组件
   :header-rows: 1

   * - 初始化函数
     - 注册内容
   * - ``LLVMInitializeXXXTargetInfo``
     - Triple → Target 映射
   * - ``LLVMInitializeXXXTarget``
     - TargetMachine 工厂
   * - ``LLVMInitializeXXXTargetMC``
     - MC 层组件
   * - ``LLVMInitializeXXXAsmPrinter``
     - 汇编输出
   * - ``LLVMInitializeXXXAsmParser``
     - 汇编解析
   * - ``LLVMInitializeXXXDisassembler``
     - 反汇编器

这些函数通常在 ``XXX.h`` 中声明，在 ``XXX.cpp`` 中实现。

在 CMake 中添加新 Target
==============================

在 LLVM 源码树中添加一个新目标需要：

.. code-block:: text

每个 Target 目录的 ``CMakeLists.txt`` 需要声明它包含的 TableGen 文件
和 C++ 源文件：

.. code-block:: cmake

   # llvm/lib/Target/MyTarget/CMakeLists.txt
   set(MyTargetCodegenSources
       MyTargetISelLowering.cpp
       MyTargetInstrInfo.cpp
       MyTargetRegisterInfo.cpp
       MyTargetSubtarget.cpp
       MyTargetTargetMachine.cpp
   )

   tablegen(MyTargetGenRegisterInfo.inc -gen-register-info)
   tablegen(MyTargetGenInstrInfo.inc -gen-instr-info)
   tablegen(MyTargetGenDAGISel.inc -gen-dag-isel)
   tablegen(MyTargetGenAsmWriter.inc -gen-asm-writer)
   tablegen(MyTargetGenSubtargetInfo.inc -gen-subtarget)

   add_llvm_target(MyTargetCodegen ${MyTargetCodegenSources})

实际上，添加一个新目标（从零开始）的工作量很大——需要实现所有后端组件。
但框架提供了清晰的骨架：

.. code-block:: cpp

   // 最小 TargetMachine
   class MyTargetTargetMachine : public LLVMTargetMachine {
   public:
       MyTargetTargetMachine(const Target &T, const Triple &TT,
                             StringRef CPU, StringRef FS,
                             const TargetOptions &Options,
                             Optional<Reloc::Model> RM,
                             Optional<CodeModel::Model> CM,
                             CodeGenOpt::Level OL, bool JIT)
           : LLVMTargetMachine(T, "e-m:e-p:32:32", TT, CPU, FS, Options) {}
   };

每个 Target 的命名空间
===========================

LLVM 中每个后端都在独立的命名空间中：

.. code-block:: cpp

   namespace llvm {
       // X86 后端
       namespace X86 { /* ... */ }

       // AArch64 后端
       namespace AArch64 { /* ... */ }

       // RISCV 后端
       namespace RISCV { /* ... */ }
   }

这些命名空间中通常定义：

- 目标特定的枚举（如 ``X86::ADD32rr`` ）
- 目标特定的函数（如 ``X86::getSysIdxFromInstr`` ）
- 目标特定的类型

调试 Target 注册
====================

.. code-block:: console

   # 查看 LLVM 支持的架构
   $ llc --version
     Registered Targets:
       aarch64    - AArch64 (little endian)
       arm        - ARM
       riscv64    - RISC-V 64-bit
       x86        - X86 (32-bit)
       x86-64     - X86 (64-bit)
       ...

   # 查看特定目标的信息
   $ llc -march=x86-64 -mcpu=help

--------

*本文由 ``agents.md`` 驱动，项目：deep_dive_into_llvm*
