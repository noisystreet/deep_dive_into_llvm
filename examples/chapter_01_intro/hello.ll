; ============================================================
; 一个简单的 LLVM IR 程序
; 使用 lli 直接运行：
;   lli simple.ll
; 或用 llc 编译为机器码：
;   llc simple.ll -o simple.s
; ============================================================

; 声明外部函数 printf
declare i32 @printf(i8*, ...)

; 定义全局字符串常量
@format = private unnamed_addr constant [12 x i8] c"Hello, LLVM\0A\00"

; 定义 main 函数
define i32 @main() {
entry:
  ; 调用 printf
  %call = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([12 x i8], [12 x i8]* @format, i32 0, i32 0))
  ret i32 0
}
