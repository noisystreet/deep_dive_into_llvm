// 示例 6.1：向量加法降级管道
// 用法：
//   mlir-opt vector_add.mlir \
//       --convert-scf-to-cf \
//       --convert-arith-to-llvm \
//       --convert-func-to-llvm \
//       --reconcile-unrealized-casts

func.func @add(%a: i32, %b: i32) -> i32 {
  %sum = arith.addi %a, %b : i32
  func.return %sum : i32
}
