"""统一 Matplotlib 风格：浅入深出 LLVM 项目"""
import matplotlib
import matplotlib.pyplot as plt

# 使用 Noto Sans CJK 支持中文
matplotlib.rcParams.update({
    'font.family': ['Noto Sans CJK JP', 'DejaVu Sans'],
    'font.size': 11,
    'axes.unicode_minus': False,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'figure.facecolor': 'white',
    'svg.fonttype': 'path',  # 文字转为路径，RTD 上无需中文字体
})

# 书籍配色方案
COLORS = {
    'primary': '#2C5F8A',     # 深蓝（LLVM 主题色）
    'secondary': '#E2882C',   # 橙（MLIR 主题色）
    'accent': '#4CAF50',      # 绿
    'gray': '#757575',
    'light_bg': '#F5F5F5',
    'white': '#FFFFFF',
}

def setup_figure(width=8, height=4.5):
    """创建统一风格的 Figure。"""
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_facecolor(COLORS['white'])
    fig.patch.set_facecolor(COLORS['white'])
    return fig, ax
