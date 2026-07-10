"""
LLVM 优化管道图：Pass Pipeline 流程
输出: _static/figures/llvm_opt_pipeline.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=3.0)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis('off')

    stages = [
        (0.3, 'IR Input', 'LLVM IR\nfrom Frontend', COLORS['primary']),
        (2.5, 'Analysis\nPasses', 'Dominator\nLoopInfo\nAliasAnalysis', '#6C8EB2'),
        (4.7, 'Transform\nPasses', 'Inline\nGVN\nSCCP\nLSR', COLORS['accent']),
        (6.9, 'Vectorization', 'Loop Vectorize\nSLP Vectorize', '#9C27B0'),
        (9.1, 'IR Output', 'Optimized\nLLVM IR', COLORS['primary']),
    ]

    for x, title, desc, color in stages:
        rect = mpatches.FancyBboxPatch(
            (x - 0.9, 0.8), 1.8, 1.8,
            boxstyle="round,pad=0.1", facecolor=color, alpha=0.12,
            edgecolor=color, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x, 2.15, title, ha='center', va='top',
                fontsize=10, fontweight='bold', color=color)
        ax.text(x, 1.5, desc, ha='center', va='center',
                fontsize=8, color=COLORS['gray'])

    # 箭头
    for i in range(len(stages) - 1):
        x1 = stages[i][0] + 1.0
        x2 = stages[i+1][0] - 1.0
        ax.annotate('', xy=(x2, 1.7), xytext=(x1, 1.7),
                    arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1.5))

    # -O 等级标注
    ax.text(5, 0.35, 'opt -O2 -passes="default<O2>" input.ll -o output.ll',
            ha='center', va='center', fontsize=8, style='italic', color=COLORS['gray'])
    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/llvm_opt_pipeline.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
