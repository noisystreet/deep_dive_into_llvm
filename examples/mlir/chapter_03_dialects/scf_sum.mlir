// 示例 3.1：scf.for 循环求和
// 用法：
//   mlir-opt scf_sum.mlir
//   mlir-opt scf_sum.mlir --convert-scf-to-cf --convert-arith-to-llvm \
//       --convert-func-to-llvm --reconcile-unrealized-casts

func.func @sum(%n: index) -> i32 {
  %c0_i32 = arith.constant 0 : i32
  %c1 = arith.constant 1 : index
  %c0 = arith.constant 0 : index
  %result = scf.for %i = %c0 to %n step %c1
      iter_args(%acc = %c0_i32) -> i32 {
    %i_i32 = arith.index_cast %i : index to i32
    %next = arith.addi %acc, %i_i32 : i32
    scf.yield %next : i32
  }
  func.return %result : i32
}
