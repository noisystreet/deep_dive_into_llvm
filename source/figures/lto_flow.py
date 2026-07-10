"""
LTO/ThinLTO 链接时优化流程图
输出: _static/figures/lto_flow.svg
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

    # 传统编译
    ax.text(0.5, 4.2, '传统编译', fontsize=10, fontweight='bold', color=COLORS['gray'])
    for i, (name, x) in enumerate([('a.c → a.o', 0.5), ('b.c → b.o', 3.0), ('c.c → c.o', 5.5)]):
        rect = mpatches.FancyBboxPatch((x, 3.3), 1.8, 0.6, boxstyle="round,pad=0.05",
                                        facecolor=COLORS['gray'], alpha=0.15, edgecolor=COLORS['gray'], lw=1)
        ax.add_patch(rect)
        ax.text(x + 0.9, 3.6, name, ha='center', va='center', fontsize=7.5, color=COLORS['gray'])
    # 链接箭头
    ax.annotate('', xy=(8.0, 3.6), xytext=(7.5, 3.6),
                arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1.5))
    ax.text(8.5, 3.6, 'ld → a.out', ha='center', va='center', fontsize=7.5, color=COLORS['gray'])

    # 分隔
    ax.plot([0, 10], [2.9, 2.9], '--', color='#DDD', lw=1)

    # Full LTO
    ax.text(0.5, 2.6, 'Full LTO', fontsize=10, fontweight='bold', color=COLORS['primary'])
    rect = mpatches.FancyBboxPatch((0.3, 1.6), 4.2, 0.7, boxstyle="round,pad=0.08",
                                    facecolor=COLORS['primary'], alpha=0.1, edgecolor=COLORS['primary'], lw=2)
    ax.add_patch(rect)
    ax.text(2.4, 1.95, 'llvm-lto: 合并所有 .o → 全局 IR → 优化', ha='center', va='center',
            fontsize=8, color=COLORS['primary'], fontweight='bold')
    ax.annotate('', xy=(4.6, 1.95), xytext=(4.8, 1.95),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=2))
    ax.text(5.5, 1.95, '单模块 → 机器码', ha='center', va='center', fontsize=7.5, color=COLORS['gray'])

    # ThinLTO
    ax.text(0.5, 1.1, 'ThinLTO', fontsize=10, fontweight='bold', color=COLORS['accent'])
    rect = mpatches.FancyBboxPatch((0.3, 0.1), 9.4, 0.7, boxstyle="round,pad=0.08",
                                    facecolor=COLORS['accent'], alpha=0.1, edgecolor=COLORS['accent'], lw=2)
    ax.add_patch(rect)
    ax.text(5, 0.45, '各 .o 独立编译 + 轻量索引同步 → 跨模块内联 + 并行代码生成',
            ha='center', va='center', fontsize=8, color=COLORS['accent'], fontweight='bold')

    # 优缺点标注
    ax.text(7.0, 2.2, '⚠ 内存大、慢', ha='center', fontsize=7, color=COLORS['gray'])
    ax.text(8.5, 0.8, '✅ 快、可扩展', ha='center', fontsize=7, color=COLORS['gray'])

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/lto_flow.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
