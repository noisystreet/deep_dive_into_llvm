"""
LLVM 项目生态图：子项目及其关系
输出: _static/figures/llvm_ecosystem.svg
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

    # 前端层
    frontends = ['Clang (C/C++)', 'Flang (Fortran)', 'rustc (Rust)', 'swiftc (Swift)']
    ax.text(5, 4.7, '前端 (Frontend)', ha='center', fontsize=12, fontweight='bold', color=COLORS['primary'])
    for i, name in enumerate(frontends):
        x = 1.0 + i * 2.3
        rect = mpatches.FancyBboxPatch((x, 3.8), 1.8, 0.7, boxstyle="round,pad=0.08",
                                        facecolor=COLORS['primary'], alpha=0.1, edgecolor=COLORS['primary'], lw=1.5)
        ax.add_patch(rect)
        ax.text(x + 0.9, 4.15, name, ha='center', va='center', fontsize=8, color=COLORS['primary'])

    # LLVM IR 核心
    core = mpatches.FancyBboxPatch((2.5, 2.3), 5.0, 1.0, boxstyle="round,pad=0.1",
                                    facecolor=COLORS['secondary'], alpha=0.15, edgecolor=COLORS['secondary'], lw=2.5)
    ax.add_patch(core)
    ax.text(5, 2.8, 'LLVM Core: LLVM IR + Pass Framework', ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['secondary'])

    # 后端架构
    backends = ['X86 Backend', 'ARM/AArch64', 'RISCV', 'NVPTX / AMDGPU']
    ax.text(5, 1.9, '后端 (Backend)', ha='center', fontsize=12, fontweight='bold', color=COLORS['accent'])
    for i, name in enumerate(backends):
        x = 1.0 + i * 2.3
        rect = mpatches.FancyBboxPatch((x, 1.0), 1.8, 0.7, boxstyle="round,pad=0.08",
                                        facecolor=COLORS['accent'], alpha=0.1, edgecolor=COLORS['accent'], lw=1.5)
        ax.add_patch(rect)
        ax.text(x + 0.9, 1.35, name, ha='center', va='center', fontsize=8, color=COLORS['accent'])

    # 周边工具
    extra = ['LLD (Linker)', 'compiler-rt', 'libc++ / libc++abi', 'LLDB (Debugger)']
    ax.text(5, 0.5, 'LLVM 工具链', ha='center', fontsize=11, fontweight='bold', color=COLORS['gray'])
    for i, name in enumerate(extra):
        x = 0.5 + i * 2.4
        ax.text(x + 1.2, 0.2, name, ha='center', va='center', fontsize=7.5,
                color=COLORS['gray'], style='italic')

    # 箭头 Frontend → Core
    ax.annotate('', xy=(5, 3.3), xytext=(5, 3.6),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=2))
    # 箭头 Core → Backend
    ax.annotate('', xy=(5, 2.3), xytext=(5, 2.0),
                arrowprops=dict(arrowstyle='->', color=COLORS['accent'], lw=2))

    return fig

if __name__ == '__main__':
    fig = draw()
    out = sys.argv[1] if len(sys.argv) > 1 else '../source/_static/figures/llvm_ecosystem.svg'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(f"Saved: {out}")
