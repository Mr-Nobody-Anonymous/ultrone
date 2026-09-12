# Copyright (c) Ultrone Contributors. All rights reserved.
"""Auction mechanisms for resource allocation and mechanism design."""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Brain.Reasoning.GameTheory.Auction")


@dataclass
class AuctionConfig:
    """Configuration for auction mechanism."""
    auction_type: str = "vickrey"  # vickrey, english, dutch, sealed_bid
    reserve_price: float = 0.0


class AuctionMechanism:
    """Auction theory implementation for resource allocation.

    Supports Vickrey (second-price sealed-bid), English, Dutch,
    and sealed-bid auctions.
    """

    def __init__(self, config: Optional[AuctionConfig] = None):
        self.config = config or AuctionConfig()

    def run_auction(self, bids: Dict[str, float], num_items: int = 1) -> Dict[str, Any]:
        """Run an auction and return allocation and prices.

        Args:
            bids: Mapping of bidder_id -> bid_amount
            num_items: Number of identical items to allocate

        Returns:
            Dict with winning bids and prices
        """
        sorted_bids = sorted(bids.items(), key=lambda x: -x[1])
        winners = sorted_bids[:num_items]

        if self.config.auction_type == "vickrey":
            # Second-price: winners pay the highest losing bid
            payment = sorted_bids[num_items][1] if len(sorted_bids) > num_items else self.config.reserve_price
            payments = {bidder: payment for bidder, _ in winners}
        else:
            # First-price: winners pay their bid
            payments = dict(winners)

        return {
            "winners": dict(winners),
            "payments": payments,
            "revenue": sum(payments.values()),
            "type": self.config.auction_type,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"type": "AuctionMechanism", "auction_type": self.config.auction_type}