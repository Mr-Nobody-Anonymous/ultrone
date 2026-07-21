# Copyright (c) Ultrone Contributors. All rights reserved.
"""Live telemetry dashboard for ULTRONE training."""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger("Ultrone.Viz.TelemetryDashboard")

# Prefer an interactive GUI backend when available; fall back gracefully
import matplotlib
available_backends = matplotlib.rcsetup.all_backends
preferred = [b for b in ["TkAgg", "QtAgg", "Qt5Agg", "GTK3Agg", "WXAgg", "MacOSX"] if b in available_backends]
if preferred:
    try:
        matplotlib.use(preferred[0])
    except Exception:
        pass

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class TelemetryDashboard:
    """
    Live 2x2 telemetry dashboard for ULTRONE training.
    
    Subplots:
    - Top Left: Rolling Success Rate (%)
    - Top Right: Mutation Rate
    - Bottom Left: Average Reward per episode
    - Bottom Right: Best Novelty Score per episode
    """

    def __init__(self, max_points: int = 200) -> None:
        self.max_points = max_points
        
        # History buffers
        self.episodes: List[int] = []
        self.success_rates: List[float] = []
        self.mutation_rates: List[float] = []
        self.avg_rewards: List[float] = []
        self.novelty_scores: List[float] = []
        
        # Plot objects
        self.fig = None
        self.ax_success = None
        self.ax_mutation = None
        self.ax_reward = None
        self.ax_novelty = None
        self.line_success = None
        self.line_mutation = None
        self.line_reward = None
        self.line_novelty = None
        self._initialized = False

    def _init_plot(self) -> None:
        """Initialize matplotlib figure and axes."""
        plt.ion()
        self.fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle("ULTRONE Live Training Telemetry", fontsize=14, fontweight="bold")
        
        (self.ax_success, self.ax_mutation,
         self.ax_reward, self.ax_novelty) = axes.flatten()
        
        # Top Left: Success Rate
        self.ax_success.set_title("Rolling Success Rate (%)")
        self.ax_success.set_xlabel("Episode")
        self.ax_success.set_ylabel("Success %")
        self.line_success, = self.ax_success.plot([], [], linewidth=2, color="tab:green")
        self.ax_success.set_ylim(0, 100)
        self.ax_success.grid(True, alpha=0.3)
        
        # Top Right: Mutation Rate
        self.ax_mutation.set_title("Adaptive Mutation Rate")
        self.ax_mutation.set_xlabel("Episode")
        self.ax_mutation.set_ylabel("Mutation Rate")
        self.line_mutation, = self.ax_mutation.plot([], [], linewidth=2, color="tab:red")
        self.ax_mutation.set_ylim(0, 0.2)
        self.ax_mutation.grid(True, alpha=0.3)
        
        # Bottom Left: Average Reward
        self.ax_reward.set_title("Average Reward per Episode")
        self.ax_reward.set_xlabel("Episode")
        self.ax_reward.set_ylabel("Avg Reward")
        self.line_reward, = self.ax_reward.plot([], [], linewidth=2, color="tab:blue")
        self.ax_reward.grid(True, alpha=0.3)
        
        # Bottom Right: Best Novelty Score
        self.ax_novelty.set_title("Best Novelty Score")
        self.ax_novelty.set_xlabel("Episode")
        self.ax_novelty.set_ylabel("Novelty Score")
        self.line_novelty, = self.ax_novelty.plot([], [], linewidth=2, color="tab:purple")
        self.ax_novelty.set_ylim(0, 1.0)
        self.ax_novelty.grid(True, alpha=0.3)
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        self._initialized = True

    def update(self, episode: int, success_rate: float, mutation_rate: float,
               avg_reward: float, novelty_score: float) -> None:
        """
        Push new telemetry data and redraw.
        
        Args:
            episode: Current episode number
            success_rate: Recent success rate (0-100)
            mutation_rate: Current mutation rate
            avg_reward: Average reward over recent episodes
            novelty_score: Best novelty/fitness score
        """
        if not self._initialized:
            self._init_plot()
        
        # Append data
        self.episodes.append(episode)
        self.success_rates.append(success_rate)
        self.mutation_rates.append(mutation_rate)
        self.avg_rewards.append(avg_reward)
        self.novelty_scores.append(novelty_score)
        
        # Trim to max_points
        if len(self.episodes) > self.max_points:
            self.episodes = self.episodes[-self.max_points:]
            self.success_rates = self.success_rates[-self.max_points:]
            self.mutation_rates = self.mutation_rates[-self.max_points:]
            self.avg_rewards = self.avg_rewards[-self.max_points:]
            self.novelty_scores = self.novelty_scores[-self.max_points:]
        
        # Update lines
        self.line_success.set_data(self.episodes, self.success_rates)
        self.line_mutation.set_data(self.episodes, self.mutation_rates)
        self.line_reward.set_data(self.episodes, self.avg_rewards)
        self.line_novelty.set_data(self.episodes, self.novelty_scores)
        
        # Auto-scale x axis
        for ax in [self.ax_success, self.ax_mutation, self.ax_reward, self.ax_novelty]:
            ax.relim()
            ax.autoscale_view(scaley=False)
            if self.episodes:
                ax.set_xlim(min(self.episodes), max(self.episodes) + 1)
        
        # Special y-axis adjustments
        if self.avg_rewards:
            min_r = min(self.avg_rewards)
            max_r = max(self.avg_rewards)
            if min_r != max_r:
                self.ax_reward.set_ylim(min_r - 10, max_r + 10)
        
        try:
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except Exception as e:
            logger.debug(f"Dashboard render skipped: {e}")

    def close(self) -> None:
        """Close the dashboard window."""
        if self.fig is None:
            return
        try:
            # Save final chart for headless environments
            import os
            out = Path(__file__).resolve().parent.parent / "memory" / "telemetry_dashboard.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            self.fig.savefig(out, dpi=150, bbox_inches="tight")
            logger.info(f"Saved telemetry dashboard to {out}")
        except Exception:
            pass
        plt.close(self.fig)
        self._initialized = False


# Module-level singleton for easy access
_dashboard: Optional[TelemetryDashboard] = None


def get_dashboard(max_points: int = 200) -> TelemetryDashboard:
    """Get or create the global telemetry dashboard."""
    global _dashboard
    if _dashboard is None:
        _dashboard = TelemetryDashboard(max_points=max_points)
    return _dashboard


def update_dashboard(episode: int, success_rate: float, mutation_rate: float,
                     avg_reward: float, novelty_score: float) -> None:
    """ Convenience function to update the global dashboard."""
    dashboard = get_dashboard()
    dashboard.update(episode, success_rate, mutation_rate, avg_reward, novelty_score)


def close_dashboard() -> None:
    """Close the global dashboard."""
    global _dashboard
    if _dashboard is not None:
        _dashboard.close()
        _dashboard = None