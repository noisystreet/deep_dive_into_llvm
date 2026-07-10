"""
LLVM 三段式架构图：前端 → 优化器 → 后端
输出: _build/figures/llvm_three_stage.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=2.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.5)
    ax.axis('off')

    # 三个阶段的配置
    stages = [
        (1.0, '前端\n(Frontend)', '源代码 → AST\n→ LLVM IR', COLORS['primary']),
        (4.2, '优化器\n(Optimizer)', '分析与变换\nPass Pipeline', COLORS['accent']),
        (7.4, '后端\n(Backend)', '指令选择 → 寄存器分配\n→ 机器码', COLORS['secondary']),
    ]

    for x, title, desc, color in stages:
        # 方框
        rect = mpatches.FancyBboxPatch(
            (x, 0.5), 2.4, 1.8,
            boxstyle="round,pad=0.1", facecolor=color, alpha=0.15,
            edgecolor=color, linewidth=2
        )
        ax.add_patch(rect)
        # 标题
        ax.text(x + 1.2, 1.85, title, ha='center', va='top',
                fontsize=13, fontweight='bold', color=color)
        # 描述
        ax.text(x + 1.2, 1.0, desc, ha='center', va='center',
                fontsize=9, color=COLORS['gray'])

    # 箭头
    for x in [3.4, 6.6]:
        ax.annotate('', xy=(x + 0.3, 1.4), xytext=(x - 0.1, 1.4),
                    arrowprops=dict(arrowstyle='->', color=COLORS['gray'],
                                    lw=2))

    # 底部 LLVM IR 标注
    ax.text(5, 0.25, 'LLVM IR（唯一中间表示）', ha='center', va='center',
            fontsize=10, style='italic', color=COLORS['primary'])

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/llvm_three_stage.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
