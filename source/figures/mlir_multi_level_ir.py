"""
MLIR 多层 IR 表示图：不同的抽象层级
输出: _static/figures/mlir_multi_level_ir.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=4.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis('off')

    layers = [
        (3.5, 4.5, '高层 IR（领域相关）', 3.5, COLORS['secondary'],
         'StableHLO / TOSA\nmatmul, conv2d, reduce'),
        (2.0, 3.5, '中层 IR（结构化）', 3.5, COLORS['accent'],
         'linalg / tensor / scf\nmatmul, generic, for, if'),
        (0.5, 2.5, '低层 IR（基础）', 3.5, '#6C8EB2',
         'arith / memref / cf\nadd, load, store, br'),
        (-1.0, 1.5, 'LLVM IR', 3.5, COLORS['primary'],
         'llvm.add, llvm.load\nphi, call, alloca'),
        (-2.5, 0.5, '机器码', 3.5, '#555',
         'x86: addl, movl\nARM: ADD, LDR'),
    ]

    for y_offset, y, title, h, color, content in layers:
        rect = mpatches.FancyBboxPatch(
            (0.5, y - 0.35), 9.0, h,
            boxstyle="round,pad=0.06", facecolor=color, alpha=0.08,
            edgecolor=color, linewidth=2 if 'IR' in title else 1
        )
        ax.add_patch(rect)
        ax.text(1.0, y + h/2 - 0.35, title, ha='left', va='center',
                fontsize=10, fontweight='bold', color=color)
        ax.text(9.0, y + h/2 - 0.35, content, ha='right', va='center',
                fontsize=7.5, color=COLORS['gray'])

    # 左侧箭头标注"抽象层次"
    ax.annotate('', xy=(0.2, 1.0), xytext=(0.2, 4.0),
                arrowprops=dict(arrowstyle='->', color='#999', lw=2))
    ax.text(0.1, 2.5, '抽象层次', ha='center', va='center',
            fontsize=8, color='#999', rotation=90)

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/mlir_multi_level_ir.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
