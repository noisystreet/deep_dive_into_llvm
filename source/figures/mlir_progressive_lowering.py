"""
MLIR 渐进降级流程：高层 Dialect → 低层 Dialect → LLVM Dialect
输出: _build/figures/mlir_progressive_lowering.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=3.5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.5)
    ax.axis('off')

    # 三层架构
    layers = [
        ('领域特定层', [0.5, 2.6], [
            ('StableHLO', 0.8, COLORS['secondary']),
            ('TOSA', 3.0, COLORS['secondary']),
            ('tensor', 5.2, COLORS['secondary']),
            ('linalg', 7.4, COLORS['secondary']),
        ]),
        ('结构化层', [0.5, 1.5], [
            ('scf', 1.5, COLORS['accent']),
            ('cf', 4.0, COLORS['accent']),
            ('arith', 6.5, COLORS['accent']),
        ]),
        ('底层 IR', [0.5, 0.4], [
            ('LLVM Dialect', 2.5, COLORS['primary']),
            ('LLVM IR', 6.0, COLORS['primary']),
        ]),
    ]

    for layer_name, (x_start, y), items in layers:
        # 层背景
        rect = mpatches.FancyBboxPatch(
            (x_start, y - 0.15), 9.0 - x_start, 0.8,
            boxstyle="round,pad=0.05", facecolor='#FAFAFA',
            edgecolor='#DDD', linewidth=1, linestyle='--'
        )
        ax.add_patch(rect)
        # 层名
        ax.text(x_start + 0.15, y + 0.5, layer_name,
                fontsize=8, color=COLORS['gray'], va='center')

        for name, x, color in items:
            box = mpatches.FancyBboxPatch(
                (x, y), 1.6, 0.5,
                boxstyle="round,pad=0.05", facecolor=color, alpha=0.15,
                edgecolor=color, linewidth=1.5
            )
            ax.add_patch(box)
            ax.text(x + 0.8, y + 0.25, name, ha='center', va='center',
                    fontsize=10, fontweight='bold', color=color)

    # 降级箭头（向下）
    arrows_data = [
        (1.6, 2.6, 1.6, 2.35),
        (3.8, 2.6, 3.8, 2.35),
        (6.0, 2.6, 6.0, 2.35),
        (8.2, 2.6, 8.2, 2.35),
        (2.3, 1.5, 2.3, 1.25),
        (4.8, 1.5, 4.8, 1.25),
        (7.3, 1.5, 7.3, 1.25),
    ]
    for xs, ys, xe, ye in arrows_data:
        ax.annotate('', xy=(xe, ye), xytext=(xs, ys),
                    arrowprops=dict(arrowstyle='->', color='#999', lw=1))

    # 大箭头说明
    ax.annotate('Progressive Lowering', xy=(9.5, 2.0),
                xytext=(9.5, 2.0), fontsize=9, color=COLORS['gray'],
                rotation=90, va='center')

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/mlir_progressive_lowering.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
