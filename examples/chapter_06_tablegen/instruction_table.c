// ============================================================
// 表驱动生成的示例：C 代码中使用 TableGen 生成的指令信息
// 此文件展示 TableGen 所解决问题的本质（表格驱动逻辑）
// ============================================================

#include <stdio.h>
#include <string.h>

// 模拟 TableGen 生成的指令信息表
typedef struct {
    const char* name;
    const char* mnemonic;
    int         opcode;
    int         num_operands;
    const char* format;  // "R", "I", "J" 等
} InstructionInfo;

// 这个表在 LLVM 中是由 TableGen 从 .td 文件自动生成的
static InstructionInfo instruction_table[] = {
    {"ADD",  "add",  0x00, 3, "R"},
    {"SUB",  "sub",  0x01, 3, "R"},
    {"MUL",  "mul",  0x02, 3, "R"},
    {"DIV",  "div",  0x03, 3, "R"},
    {"ADDI", "addi", 0x04, 3, "I"},
    {"SUBI", "subi", 0x05, 3, "I"},
    {"LW",   "lw",   0x06, 2, "I"},
    {"SW",   "sw",   0x07, 2, "I"},
    {"BEQ",  "beq",  0x08, 3, "J"},
    {"JMP",  "jmp",  0x09, 1, "J"},
    {NULL,   NULL,   0,    0, NULL}
};

void print_instruction_table() {
    printf("Instruction Table:\n");
    printf("%-10s %-10s %-6s %-12s %s\n",
           "Name", "Mnemonic", "Opcode", "Operands", "Format");
    printf("----------------------------------------------------\n");

    for (int i = 0; instruction_table[i].name != NULL; i++) {
        printf("%-10s %-10s 0x%02X   %-12d %s\n",
               instruction_table[i].name,
               instruction_table[i].mnemonic,
               instruction_table[i].opcode,
               instruction_table[i].num_operands,
               instruction_table[i].format);
    }
}

int main() {
    print_instruction_table();
    return 0;
}
