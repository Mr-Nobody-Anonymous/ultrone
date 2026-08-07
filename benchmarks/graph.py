# Copyright (c) Ultrone Contributors. All rights reserved.
"""Benchmark Graph — generate improvement plots from benchmark history.

Produces a matplotlib line chart of accuracy over time for one or more
benchmark names, saved to a PNG file. Helps visualize the self-improvement
loop's progress and regressions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .history import BenchmarkHistory

logger = logging.getLogger("Ultrone.Benchmarks.Graph")


class BenchmarkGraph:
    """Generates benchmark improvement charts.

    Parameters
    ----------
    history : Optional[BenchmarkHistory]
        The history source. Defaults to a fresh instance.
    """

    def __init__(self, history: Optional[BenchmarkHistory] = None) -> None:
        self.history = history or BenchmarkHistory()

    def plot(
        self,
        names: List[str],
        output_path: str = "benchmarks/improvement.png",
        title: str = "Benchmark Improvement Over Time",
    ) -> str:
        """Plot accuracy over time for the given benchmark names.

        Parameters
        ----------
        names
            Benchmark names to plot. If empty, plots all known benchmarks.
        output_path
            Where to save the PNG.
        title
            Chart title.

        Returns
        -------
        str
            The absolute path of the saved chart.
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            logger.error("matplotlib is required for graph generation: %s", exc)
            raise

        if not names:
            stats = self.history.get_stats()
            names = list(stats.get("benchmarks", {}).keys())
        if not names:
            logger.warning("No benchmark history to plot")
            return ""

        fig, ax = plt.subplots(figsize=(10, 6))
        for name in names:
            timestamps, accuracies = self.history.get_timeseries(name)
            if not timestamps:
                continue
            # Normalize timestamps to relative minutes for readability.
            base = timestamps[0]
            xs = [(t - base) / 60.0 for t in timestamps]
            ax.plot(xs, accuracies, marker="o", label=name)

        ax.set_xlabel("Elapsed time (minutes)")
        ax.set_ylabel("Accuracy")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0.0, 1.05)

        fig.tight_layout()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out), dpi=150)
        plt.close(fig)
        logger.info("Saved benchmark graph to %s", out.resolve())
        return str(out.resolve())
