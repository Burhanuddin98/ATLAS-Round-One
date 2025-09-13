# materials_plot.py — Matplotlib mini-plot for material curves
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class MatPlotMini(FigureCanvas):
    def __init__(self, width=3.5, height=2.2, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)

    def plot_absorption(self, freqs, alpha, scatter=None, title=None):
        self.ax.clear()
        f = np.asarray(freqs, dtype=float)
        a = np.asarray(alpha, dtype=float)
        self.ax.semilogx(f, a, marker='o', linewidth=1)
        self.ax.set_ylim(0, 1.05)
        self.ax.set_xlim(max(20, f.min()*0.9), f.max()*1.1)
        self.ax.grid(True, which='both', alpha=0.3)
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Absorption α")
        if title:
            self.ax.set_title(title, fontsize=10)
        # optional scatter overlay
        if scatter is not None:
            s = np.asarray(scatter, dtype=float)
            self.ax.semilogx(f, s, linestyle='--', alpha=0.6)
            self.ax.legend(["α", "scatter"], fontsize=8, loc='lower right')
        self.draw()
