; ============================================================
; LLVM IR 核心示例：展示基本指令和 SSA 形式
; 编译方法：
;   llc ir_basics.ll -o ir_basics.s
; ============================================================

target triple = "x86_64-unknown-linux-gnu"

; 全局变量定义
@global_var = global i32 42

; 函数定义：计算 a * b + c
define i32 @compute(i32 %a, i32 %b, i32 %c) {
entry:
  ; SSA 形式：每个变量只赋值一次
  %mul = mul i32 %a, %b
  %add = add i32 %mul, %c
  ret i32 %add
}

; 条件分支示例
define i32 @max(i32 %x, i32 %y) {
entry:
  %cmp = icmp sgt i32 %x, %y
  br i1 %cmp, label %then, label %else

then:
  ret i32 %x

else:
  ret i32 %y
}

; GEP 指令示例
define i32* @get_element(i32* %arr, i64 %index) {
entry:
  %ptr = getelementptr i32, i32* %arr, i64 %index
  ret i32* %ptr
}

; 循环示例（使用 phi 节点）
define i32 @sum(i32 %n) {
entry:
  br label %loop

loop:
  %i = phi i32 [ 0, %entry ], [ %next, %loop ]
  %acc = phi i32 [ 0, %entry ], [ %sum, %loop ]
  %next = add i32 %i, 1
  %sum = add i32 %acc, %i
  %done = icmp eq i32 %next, %n
  br i1 %done, label %exit, label %loop

exit:
  ret i32 %acc
}
