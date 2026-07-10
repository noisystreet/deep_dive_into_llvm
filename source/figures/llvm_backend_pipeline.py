"""
LLVM 后端代码生成管道图
输出: _static/figures/llvm_backend_pipeline.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9.5, height=4.0)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # 主阶段 (上排)
    stages = [
        (0.2, 2.5, '指令选择\n(SelectionDAG)', 'DAGToDAG\nISel', COLORS['primary']),
        (2.5, 2.5, '指令调度\n(Scheduling)', 'Pre-RA\nSched', '#6C8EB2'),
        (4.8, 2.5, '寄存器分配\n(Register Alloc)', 'Greedy\nRA', COLORS['accent']),
        (7.1, 2.5, '后寄存器调度\n(PostRA Sched)', 'Post-RA\nSched', '#9C27B0'),
        (9.4, 2.5, '代码输出\n(MC Layer)', 'AsmPrinter\nELF/MachO', COLORS['secondary']),
    ]

    for x, y, title, desc, color in stages:
        rect = mpatches.FancyBboxPatch(
            (x, y - 0.6), 1.8, 1.4,
            boxstyle="round,pad=0.08", facecolor=color, alpha=0.12,
            edgecolor=color, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x + 0.9, y + 0.5, title, ha='center', va='top',
                fontsize=9, fontweight='bold', color=color)
        ax.text(x + 0.9, y + 0.1, desc, ha='center', va='center',
                fontsize=7.5, color=COLORS['gray'])

    # 箭头
    for i in range(len(stages) - 1):
        x1 = stages[i][0] + 1.9
        x2 = stages[i+1][0] + 0.1
        ax.annotate('', xy=(x2, 2.2), xytext=(x1, 2.2),
                    arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1.5))

    # 下排：LLVM IR 输入 → 目标格式输出
    ax.text(0.8, 1.2, 'LLVM IR', ha='center', va='center',
            fontsize=9, color=COLORS['primary'], fontweight='bold')
    ax.text(9.5, 1.2, '.s / .o', ha='center', va='center',
            fontsize=9, color=COLORS['secondary'], fontweight='bold')
    ax.annotate('', xy=(9.0, 1.2), xytext=(1.3, 1.2),
                arrowprops=dict(arrowstyle='->', color='#CCC', lw=3))

    # 底部说明
    ax.text(5, 0.2, 'llc input.bc -o output.s -mcpu=skylake',
            ha='center', va='center', fontsize=8, style='italic', color=COLORS['gray'])
    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/llvm_backend_pipeline.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
