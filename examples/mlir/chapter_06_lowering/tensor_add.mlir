// 示例 6.2：linalg 向量加法 → scf 循环
// 用法（需先 bufferize，再展开循环）：
//   mlir-opt tensor_add.mlir \
//       --one-shot-bufferize="bufferize-function-boundaries" \
//       --convert-linalg-to-loops

func.func @add(%a: tensor<4xf32>, %b: tensor<4xf32>) -> tensor<4xf32> {
  %init = tensor.empty() : tensor<4xf32>
  %0 = linalg.elemwise_binary {fun = #linalg.binary_fn<add>}
    ins(%a, %b : tensor<4xf32>, tensor<4xf32>)
    outs(%init : tensor<4xf32>) -> tensor<4xf32>
  func.return %0 : tensor<4xf32>
}
