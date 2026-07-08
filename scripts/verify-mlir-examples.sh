#!/bin/bash
# MLIR 示例验证脚本
# ====================
# 用法: bash scripts/verify-mlir-examples.sh
# 返回码: 0=全部通过, 1=失败

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

find_mlir_opt() {
    if [ -n "${MLIR_OPT:-}" ] && command -v "$MLIR_OPT" &>/dev/null; then
        echo "$MLIR_OPT"
        return
    fi
    for candidate in mlir-opt mlir-opt-19 mlir-opt-18 mlir-opt-17; do
        if command -v "$candidate" &>/dev/null; then
            echo "$candidate"
            return
        fi
    done
    # apt.llvm.org 安装的 mlir-opt 通常在 /usr/lib/llvm-N/bin/
    for dir in /usr/lib/llvm-*/bin; do
        if [ -x "$dir/mlir-opt" ]; then
            echo "$dir/mlir-opt"
            return
        fi
        for candidate in mlir-opt-19 mlir-opt-18 mlir-opt-17; do
            if [ -x "$dir/$candidate" ]; then
                echo "$dir/$candidate"
                return
            fi
        done
    done
    return 1
}

MLIR_OPT_BIN="$(find_mlir_opt)" || {
    echo "错误: 未找到 mlir-opt。请安装 LLVM/MLIR 工具链或设置 MLIR_OPT 环境变量。"
    exit 1
}

echo "使用 mlir-opt: $MLIR_OPT_BIN"
echo ""

run_test() {
    local name="$1"
    local file="$2"
    shift 2
    local passes=("$@")

    echo -n "  $name ... "
    if [ ! -f "$PROJECT_ROOT/$file" ]; then
        echo "失败 (文件不存在: $file)"
        return 1
    fi

    if "$MLIR_OPT_BIN" "$PROJECT_ROOT/$file" "${passes[@]}" >/dev/null 2>&1; then
        echo "通过"
        return 0
    else
        echo "失败"
        "$MLIR_OPT_BIN" "$PROJECT_ROOT/$file" "${passes[@]}" 2>&1 | tail -5
        return 1
    fi
}

FAILED=0

echo "=== 解析测试 ==="
run_test "vector_add 解析" "examples/mlir/chapter_06_lowering/vector_add.mlir" || FAILED=1
run_test "tensor_add 解析" "examples/mlir/chapter_06_lowering/tensor_add.mlir" || FAILED=1
run_test "scf_sum 解析" "examples/mlir/chapter_03_dialects/scf_sum.mlir" || FAILED=1

echo ""
echo "=== 降级管道测试 ==="
run_test "vector_add → LLVM Dialect" "examples/mlir/chapter_06_lowering/vector_add.mlir" \
    --convert-scf-to-cf \
    --convert-arith-to-llvm \
    --convert-func-to-llvm \
    --reconcile-unrealized-casts || FAILED=1

run_test "tensor_add → scf 循环" "examples/mlir/chapter_06_lowering/tensor_add.mlir" \
    --one-shot-bufferize=bufferize-function-boundaries \
    --convert-linalg-to-loops || FAILED=1

run_test "scf_sum → LLVM Dialect" "examples/mlir/chapter_03_dialects/scf_sum.mlir" \
    --convert-scf-to-cf \
    --convert-arith-to-llvm \
    --convert-func-to-llvm \
    --reconcile-unrealized-casts || FAILED=1

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "✓ 所有 MLIR 示例验证通过。"
    exit 0
else
    echo "✗ 部分 MLIR 示例验证失败。"
    exit 1
fi
