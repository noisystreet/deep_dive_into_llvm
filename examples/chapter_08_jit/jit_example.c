// ============================================================
// JIT 使用示例（概念展示）
// 实际使用 LLVM JIT 需要通过 LLVM C++ API 编程
// 此文件展示 JIT 要解决的问题场景
// ============================================================

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

// 模拟 JIT 编译的函数指针类型
typedef int (*jit_compiled_func)(int);

// 模拟 JIT 编译：在运行时生成并执行代码
// 真实的 LLVM ORC JIT 会在运行时将 IR 编译为机器码
jit_compiled_func jit_compile(const char* ir_code) {
    printf("JIT Compiling IR code:\n%s\n", ir_code);
    printf("→ 实际由 LLVM ORC JIT 完成编译\n");

    // 这里返回一个模拟的编译结果函数
    // 真实场景下，ORC JIT 会返回一个函数指针
    static int counter = 0;
    counter++;
    printf("  编译完成！(模拟 #%d)\n", counter);
    return NULL;
}

// 模拟 LLJIT 的使用方式
void lljit_example() {
    const char* ir_module = R"(
define i32 @add(i32 %a, i32 %b) {
  %sum = add i32 %a, %b
  ret i32 %sum
}
)";

    printf("=== LLJIT Example ===\n");
    jit_compile(ir_module);
    printf("\n");

    // 演示 Lazy Compilation
    const char* lazy_ir = R"(
define i32 @lazy_func(i32 %n) {
  %result = mul i32 %n, 2
  ret i32 %result
}
)";

    printf("惰性编译：函数在首次调用时才编译\n");
    jit_compile(lazy_ir);
}

int main() {
    lljit_example();
    return 0;
}
