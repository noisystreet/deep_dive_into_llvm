"""
MLIR 编译流程图：从源代码到机器码的 Dialect 降级路径
输出: _static/figures/mlir_compilation_flow.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=5.0)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis('off')

    # 四个主要阶段
    stages = [
        (0.3, 4.0, 4.2, 0.8, 'Frontend\nDialects', 'StableHLO\nTOSA\ntensor', COLORS['secondary']),
        (0.3, 2.8, 4.2, 0.8, 'Compute\nDialects', 'linalg\nscf\narith', COLORS['accent']),
        (0.3, 1.6, 4.2, 0.8, 'Lowering\nDialects', 'cf\nmemref\nfunc', '#6C8EB2'),
        (0.3, 0.4, 4.2, 0.8, 'LLVM\nDialect', 'llvm func\nllvm add\n→ LLVM IR', COLORS['primary']),
    ]

    for x, y, w, h, title, desc, color in stages:
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.08", facecolor=color, alpha=0.12,
            edgecolor=color, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x + 0.3, y + h/2, title, ha='left', va='center',
                fontsize=10, fontweight='bold', color=color)
        ax.text(x + w - 0.3, y + h/2, desc, ha='right', va='center',
                fontsize=8, color=COLORS['gray'])

    # 降级箭头
    for i in range(3):
        y_start = stages[i][1] + stages[i][3] - 0.1
        y_end = stages[i+1][1] + 0.15
        ax.annotate('', xy=(2.4, y_end), xytext=(2.4, y_start),
                    arrowprops=dict(arrowstyle='->', color='#999', lw=2))

    # 右侧：渐进降级示意图
    ax.text(5.8, 4.4, 'Progressive Lowering', fontsize=11,
            fontweight='bold', color=COLORS['gray'])
    
    steps = [
        (6.5, 3.8, 'High-Level', 'StableHLO → Tensor → Linalg', COLORS['secondary']),
        (6.5, 3.0, 'Mid-Level', 'Linalg → SCF → Affine', COLORS['accent']),
        (6.5, 2.2, 'Low-Level', 'SCF → CF → Arith', '#6C8EB2'),
        (6.5, 1.4, 'Final', 'Arith + MemRef + Func → LLVM', COLORS['primary']),
    ]
    for x, y, title, desc, color in steps:
        ax.text(x, y, f'{title}:', ha='left', va='center',
                fontsize=8, fontweight='bold', color=color)
        ax.text(x + 1.5, y, desc, ha='left', va='center',
                fontsize=7.5, color=COLORS['gray'])

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/mlir_compilation_flow.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
