"""
ORC JIT 架构图：JITDylib + Layer 模型
输出: _static/figures/orc_jit_architecture.svg
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from style import setup_figure, COLORS
import matplotlib.patches as mpatches

def draw():
    fig, ax = setup_figure(width=9, height=4.0)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # JITDylib 层
    lib = mpatches.FancyBboxPatch(
        (0.3, 0.5), 9.4, 3.0,
        boxstyle="round,pad=0.1", facecolor='#FAFAFA',
        edgecolor='#999', linewidth=1.5, linestyle='--'
    )
    ax.add_patch(lib)
    ax.text(0.5, 3.15, 'JITDylib', fontsize=10, color=COLORS['gray'],
            fontweight='bold')

    # Layer 栈
    layers = [
        (0.5, 2.6, 'Compile Layer', 'Module → MachineCode\n(MachineCodeCompiler)', COLORS['primary']),
        (0.5, 1.8, 'Transform Layer', 'Optimize IR\nbefore compile', COLORS['accent']),
        (0.5, 1.0, 'Layer API', 'add() → define() →\nlookup()', '#6C8EB2'),
    ]

    for x, y, title, desc, color in layers:
        rect = mpatches.FancyBboxPatch(
            (x, y), 4.0, 0.6,
            boxstyle="round,pad=0.05", facecolor=color, alpha=0.12,
            edgecolor=color, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x + 0.2, y + 0.3, title, ha='left', va='center',
                fontsize=10, fontweight='bold', color=color)
        ax.text(x + 4.5, y + 0.3, desc, ha='left', va='center',
                fontsize=8, color=COLORS['gray'])

    # 右侧：查找机制
    lookup_box = mpatches.FancyBboxPatch(
        (5.5, 1.2), 4.0, 1.8,
        boxstyle="round,pad=0.1", facecolor=COLORS['secondary'], alpha=0.08,
        edgecolor=COLORS['secondary'], linewidth=1.5
    )
    ax.add_patch(lookup_box)
    ax.text(7.5, 2.6, 'Symbol Lookup', ha='center', va='center',
            fontsize=10, fontweight='bold', color=COLORS['secondary'])
    ax.text(7.5, 2.1, 'lookup("foo")', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])
    ax.text(7.5, 1.7, '→ JITDylib.search()', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])
    ax.text(7.5, 1.4, '→ Layer.emit()', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])

    # 箭头：Layer 之间
    for y_pos in [2.3, 1.5]:
        ax.annotate('', xy=(4.6, y_pos + 0.3), xytext=(4.6, y_pos - 0.3),
                    arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1))

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/orc_jit_architecture.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
