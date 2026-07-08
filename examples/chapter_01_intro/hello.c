// ============================================================
// 示例 1.1：从 C 源码到 LLVM IR
// 使用 clang 编译此文件查看生成的 IR：
//   clang -S -emit-llvm hello.c -o hello.ll
// ============================================================

#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    int x = 42;
    int y = 58;
    int result = add(x, y);
    printf("Result: %d\n", result);
    return 0;
}
