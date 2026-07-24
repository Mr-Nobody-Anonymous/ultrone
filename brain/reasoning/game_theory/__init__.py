# Copyright (c) Ultrone Contributors. All rights reserved.
"""Game Theory module for strategic decision-making.

Provides models for analyzing and solving strategic interactions:

- ``NashEquilibrium``: Nash equilibrium approximation
- ``StackelbergGame``: Leader-follower game models
- ``MinimaxSearch``: Minimax search with alpha-beta pruning
- ``CFR``: Counterfactual Regret Minimization
- ``AuctionMechanism``: Auction theory and mechanism design
- ``ZeroSumGame``: Zero-sum game solvers
- ``CooperativeGame``: Cooperative game theory (Shapley value, etc.)
"""

from .nash_equilibrium import NashEquilibrium, NashConfig
from .stackelberg import StackelbergGame, StackelbergConfig
from .minimax import MinimaxSearch, MinimaxConfig
from .cfr import CFR, CFRConfig
from .auction import AuctionMechanism, AuctionConfig
from .zero_sum import ZeroSumGame, ZeroSumConfig
from .cooperative import CooperativeGame, CooperativeConfig

__all__ = [
    "NashEquilibrium", "NashConfig",
    "StackelbergGame", "StackelbergConfig",
    "MinimaxSearch", "MinimaxConfig",
    "CFR", "CFRConfig",
    "AuctionMechanism", "AuctionConfig",
    "ZeroSumGame", "ZeroSumConfig",
    "CooperativeGame", "CooperativeConfig",
]
