// ============================================================
// FileCheck 使用示例
// 用 FileCheck 模式展示如何测试 LLVM 优化输出
// 运行：opt -passes='mem2reg' test.ll -S | FileCheck test.ll
// ============================================================

#include <stdio.h>

// CHECK: define i32 @test_mem2reg
// CHECK: %add = add i32 %a, %b
// CHECK: ret i32 %add
int test_mem2reg(int a, int b) {
    int x = a;
    int y = b;
    int z = x + y;
    return z;
}

// CHECK-LABEL: define i32 @test_constant_fold
// CHECK: ret i32 42
int test_constant_fold() {
    int a = 20;
    int b = 22;
    return a + b;
}
