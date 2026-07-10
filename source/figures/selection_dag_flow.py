"""
SelectionDAG 指令选择图：DAG 构建 → 合法化 → 选择
输出: _static/figures/selection_dag_flow.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=3.2)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis('off')

    stages = [
        (0.2, 'IR → DAG', 'LLVM IR\nSelectionDAGBuilder', COLORS['primary']),
        (2.6, 'DAG\nLegalization', 'Type Legalization\nOperation Legalization', '#6C8EB2'),
        (5.0, 'DAG\nCombine', 'Peephole Optimization\nSimplify Graph', COLORS['accent']),
        (7.4, 'Instruction\nSelection', 'DAG → MachineInstr\nPattern Matching', '#9C27B0'),
        (9.8, 'Machine DAG', 'Scheduling\n→ MIR', COLORS['secondary']),
    ]

    for x, title, desc, color in stages:
        rect = mpatches.FancyBboxPatch(
            (x - 1.0, 1.0), 2.0, 1.8,
            boxstyle="round,pad=0.08", facecolor=color, alpha=0.12,
            edgecolor=color, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x, 2.45, title, ha='center', va='top',
                fontsize=9, fontweight='bold', color=color)
        ax.text(x, 1.7, desc, ha='center', va='center',
                fontsize=7.5, color=COLORS['gray'])

    # 箭头
    for i in range(len(stages) - 1):
        x1 = stages[i][0] + 1.1
        x2 = stages[i+1][0] - 1.1
        ax.annotate('', xy=(x2, 1.9), xytext=(x1, 1.9),
                    arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1.5))

    # 底部说明
    ax.text(5, 0.35, 'DAG 优化是 LLVM 后端最关键的环节，直接影响生成代码质量',
            ha='center', va='center', fontsize=8, style='italic', color=COLORS['gray'])
    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/selection_dag_flow.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
