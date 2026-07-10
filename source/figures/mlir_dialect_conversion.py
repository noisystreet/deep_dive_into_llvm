"""
MLIR Dialect 转换过程图
输出: _static/figures/mlir_dialect_conversion.svg
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

    # 三个 Dialect 区域
    regions = [
        (0.3, 3.5, 'Source Dialect', COLORS['secondary'], 'tosa.matmul\nlinalg.generic'),
        (3.8, 3.5, 'Conversion\nPatterns', '#999', 'Pattern A\nPattern B\nPattern C'),
        (7.3, 3.5, 'Target Dialect', COLORS['primary'], 'scf.for\narith.addi\nmemref.load'),
    ]

    for x, w, title, color, content in [
        (0.3, 3.0, 'Source Dialect', COLORS['secondary'], 'tosa.matmul\nlinalg.generic'),
        (3.8, 3.0, 'Conversion\\nPatterns', '#999', 'Pattern A\\nPattern B\\nPattern C'),
        (7.3, 3.0, 'Target Dialect', COLORS['primary'], 'scf.for\\narith.addi\\nmemref.load'),
    ]:
        pass  # skip, rebuild below
    
    # 源 Dialect
    src = mpatches.FancyBboxPatch(
        (0.3, 1.2), 2.8, 2.0,
        boxstyle="round,pad=0.1", facecolor=COLORS['secondary'], alpha=0.1,
        edgecolor=COLORS['secondary'], linewidth=2
    )
    ax.add_patch(src)
    ax.text(1.7, 2.8, 'Source Dialect', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['secondary'])
    ax.text(1.7, 2.2, 'tosa.matmul', ha='center', va='center',
            fontsize=9, color=COLORS['gray'])
    ax.text(1.7, 1.8, 'linalg.generic', ha='center', va='center',
            fontsize=9, color=COLORS['gray'])

    # 转换模式
    conv = mpatches.FancyBboxPatch(
        (3.9, 1.2), 2.4, 2.0,
        boxstyle="round,pad=0.1", facecolor='#FAFAFA',
        edgecolor='#999', linewidth=1.5, linestyle='--'
    )
    ax.add_patch(conv)
    ax.text(5.1, 2.8, 'Convert', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#666')
    ax.text(5.1, 2.3, 'tosa → linalg', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])
    ax.text(5.1, 1.9, 'linalg → scf', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])
    ax.text(5.1, 1.5, 'scf → cf', ha='center', va='center',
            fontsize=8, color=COLORS['gray'])

    # 目标 Dialect
    tgt = mpatches.FancyBboxPatch(
        (7.1, 1.2), 2.6, 2.0,
        boxstyle="round,pad=0.1", facecolor=COLORS['primary'], alpha=0.1,
        edgecolor=COLORS['primary'], linewidth=2
    )
    ax.add_patch(tgt)
    ax.text(8.4, 2.8, 'Target Dialect', ha='center', va='center',
            fontsize=12, fontweight='bold', color=COLORS['primary'])
    ax.text(8.4, 2.2, 'scf.for', ha='center', va='center',
            fontsize=9, color=COLORS['gray'])
    ax.text(8.4, 1.8, 'arith.addi', ha='center', va='center',
            fontsize=9, color=COLORS['gray'])

    # 箭头
    ax.annotate('', xy=(7.0, 2.2), xytext=(3.6, 2.2),
                arrowprops=dict(arrowstyle='->', color='#999', lw=2))
    ax.annotate('', xy=(3.6, 1.6), xytext=(7.0, 1.6),
                arrowprops=dict(arrowstyle='->', color='#999', lw=2, linestyle='dashed'))

    # 标注
    ax.text(5.3, 0.85, 'Legalization', ha='center', va='center',
            fontsize=9, color=COLORS['accent'], fontweight='bold')
    ax.text(5.3, 3.3, 'Dialect Conversion Framework', ha='center', va='center',
            fontsize=9, style='italic', color=COLORS['gray'])

    # 底部 TypeConverter 说明
    rect = mpatches.FancyBboxPatch(
        (0.3, 0.1), 9.4, 0.5,
        boxstyle="round,pad=0.05", facecolor=COLORS['accent'], alpha=0.08,
        edgecolor=COLORS['accent'], linewidth=1
    )
    ax.add_patch(rect)
    ax.text(5, 0.35, 'TypeConverter: 类型映射 (tensor<4xf32> → memref<4xf32>)',
            ha='center', va='center', fontsize=8, color=COLORS['gray'])

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/mlir_dialect_conversion.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
