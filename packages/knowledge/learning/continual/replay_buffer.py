# Copyright (c) Ultrone Contributors. All rights reserved.
"""Experience replay buffers for continual learning.

Supports:
- FIFO replay buffer
- Prioritized experience replay (PER)
- Task-aware sampling
- Rehearsal
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple


@dataclass
class Experience:
    """A single experience tuple for replay."""
    state: Any
    action: Any
    reward: float
    next_state: Any
    done: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplayBuffer:
    """Simple FIFO replay buffer.

    Parameters
    ----------
    capacity : int
        Maximum number of experiences to store.
    """

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self._buffer: Deque[Experience] = deque(maxlen=capacity)

    def push(self, experience: Experience) -> None:
        """Add an experience to the buffer."""
        self._buffer.append(experience)

    def sample(self, batch_size: int) -> List[Experience]:
        """Sample a batch of experiences uniformly at random."""
        if len(self._buffer) == 0:
            return []
        batch_size = min(batch_size, len(self._buffer))
        return random.sample(list(self._buffer), batch_size)

    def __len__(self) -> int:
        return len(self._buffer)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "ReplayBuffer",
            "capacity": self.capacity,
            "current_size": len(self._buffer),
            "fill_rate": len(self._buffer) / self.capacity,
        }


class PrioritizedReplayBuffer(ReplayBuffer):
    """Prioritized Experience Replay (PER) with proportional prioritization.

    Parameters
    ----------
    capacity : int
        Maximum number of experiences.
    alpha : float
        Prioritization strength (0 = uniform, 1 = full priority).
    beta_start : float
        Initial importance-sampling weight.
    beta_frames : int
        Number of frames over which to anneal beta to 1.0.
    """

    def __init__(
        self,
        capacity: int = 10000,
        alpha: float = 0.6,
        beta_start: float = 0.4,
        beta_frames: int = 100000,
    ):
        super().__init__(capacity)
        self.alpha = alpha
        self.beta_start = beta_start
        self.beta_frames = beta_frames
        self._priorities: List[float] = []
        self._frame_count = 0
        self._eps = 1e-6

    def push(self, experience: Experience, priority: Optional[float] = None) -> None:
        """Add an experience with a priority."""
        if priority is None:
            priority = max(self._priorities) if self._priorities else 1.0
        super().push(experience)
        if len(self._priorities) < self.capacity:
            self._priorities.append(priority)
        else:
            idx = (len(self._buffer) - 1) % self.capacity
            self._priorities[idx] = priority

    def sample(self, batch_size: int) -> Tuple[List[Experience], List[float], List[int]]:
        """Sample with priorities. Returns (experiences, weights, indices)."""
        if len(self._buffer) == 0:
            return [], [], []

        priorities = self._priorities[:len(self._buffer)]
        probs = [p ** self.alpha for p in priorities]
        total = sum(probs)
        if total == 0:
            probs = [1.0] * len(priorities)
            total = len(priorities)
        probs = [p / total for p in probs]

        indices = random.choices(
            range(len(self._buffer)), weights=probs, k=min(batch_size, len(self._buffer))
        )
        experiences = [self._buffer[i] for i in indices]

        beta = min(
            1.0,
            self.beta_start + (1.0 - self.beta_start) * self._frame_count / self.beta_frames,
        )
        self._frame_count += 1

        weights = []
        N = len(self._buffer)
        for idx in indices:
            w = (N * probs[idx]) ** (-beta)
            weights.append(w)
        if weights:
            max_w = max(weights)
            weights = [w / max_w for w in weights]

        return experiences, weights, indices

    def update_priorities(self, indices: List[int], priorities: List[float]) -> None:
        """Update priorities for sampled experiences."""
        for idx, priority in zip(indices, priorities):
            if idx < len(self._priorities):
                self._priorities[idx] = max(priority, self._eps)

    def get_stats(self) -> Dict[str, Any]:
        base = super().get_stats()
        base.update({
            "type": "PrioritizedReplayBuffer",
            "alpha": self.alpha,
            "beta": min(
                1.0,
                self.beta_start + (1.0 - self.beta_start) * self._frame_count / self.beta_frames,
            ),
        })
        return base


class TaskAwareSampler:
    """Samples experiences with task-aware importance weighting.

    Ensures balanced sampling across tasks to mitigate catastrophic forgetting.
    """

    def __init__(self, num_tasks: int = 1):
        self.num_tasks = num_tasks
        self._task_counts: Dict[int, int] = {}
        self._buffer: List[Tuple[Experience, int]] = []

    def push(self, experience: Experience, task_id: int) -> None:
        self._buffer.append((experience, task_id))
        self._task_counts[task_id] = self._task_counts.get(task_id, 0) + 1

    def sample(self, batch_size: int) -> List[Experience]:
        if not self._buffer:
            return []
        # Compute task weights (inverse frequency to balance)
        total = len(self._buffer)
        task_weights = {}
        for tid, count in self._task_counts.items():
            task_weights[tid] = total / (self.num_tasks * count)

        # Normalize
        weight_sum = sum(task_weights.values())
        if weight_sum > 0:
            for tid in task_weights:
                task_weights[tid] /= weight_sum

        # Sample experiences
        sampled = random.choices(
            self._buffer,
            weights=[task_weights.get(tid, 0.0) for _, tid in self._buffer],
            k=min(batch_size, len(self._buffer)),
        )
        return [exp for exp, _ in sampled]

    def __len__(self) -> int:
        return len(self._buffer)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "TaskAwareSampler",
            "total_samples": len(self._buffer),
            "task_counts": self._task_counts,
            "num_tasks": self.num_tasks,
        }
