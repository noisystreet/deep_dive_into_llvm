"""
GPU Kernel Launch 流程图：host → device → kernel
输出: _static/figures/gpu_launch_flow.svg
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

    # Host 侧
    host = mpatches.FancyBboxPatch((0.3, 2.2), 4.0, 1.0, boxstyle="round,pad=0.08",
                                    facecolor=COLORS['primary'], alpha=0.1, edgecolor=COLORS['primary'], lw=2)
    ax.add_patch(host)
    ax.text(2.3, 2.7, 'Host (CPU)', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['primary'])
    ax.text(2.3, 2.2, 'gpu.launch func @kernel(...)', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])

    # Kernel 侧
    kernel = mpatches.FancyBboxPatch((5.7, 2.2), 4.0, 1.0, boxstyle="round,pad=0.08",
                                      facecolor=COLORS['secondary'], alpha=0.1, edgecolor=COLORS['secondary'], lw=2)
    ax.add_patch(kernel)
    ax.text(7.7, 2.7, 'Device (GPU)', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['secondary'])
    ax.text(7.7, 2.2, 'gridDim × blockDim × kernel', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])

    # 启动箭头
    ax.annotate('', xy=(5.6, 2.7), xytext=(4.4, 2.7),
                arrowprops=dict(arrowstyle='->', color='#999', lw=2))

    # 下排：网格层次
    grid = mpatches.FancyBboxPatch((0.3, 0.3), 9.4, 1.3, boxstyle="round,pad=0.08",
                                    facecolor='#FAFAFA', edgecolor='#DDD', lw=1, linestyle='--')
    ax.add_patch(grid)
    ax.text(0.8, 1.2, 'Grid', ha='left', va='center',
            fontsize=10, fontweight='bold', color='#999')

    blocks = ['Block 0\n(shared mem)', 'Block 1', 'Block 2', 'Block N']
    for i, name in enumerate(blocks):
        x = 0.5 + i * 2.3
        rect = mpatches.FancyBboxPatch((x, 0.4), 1.8, 0.6, boxstyle="round,pad=0.05",
                                        facecolor=COLORS['accent'], alpha=0.1, edgecolor=COLORS['accent'], lw=1.2)
        ax.add_patch(rect)
        ax.text(x + 0.9, 0.7, name, ha='center', va='center',
                fontsize=6.5, color=COLORS['accent'])

    # Vertical arrow from launch to grid
    ax.annotate('', xy=(2.3, 1.6), xytext=(2.3, 2.1),
                arrowprops=dict(arrowstyle='->', color='#CCC', lw=1))
    ax.text(3.0, 1.85, 'gpu.launch', ha='center', va='center',
            fontsize=7, color='#999')

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/gpu_launch_flow.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
