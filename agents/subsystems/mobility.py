# Copyright (c) Ultrone Contributors. All rights reserved.
"""Compatibility shim -- MobilitySubsystem now lives in ``locomotion.py``."""

from agents.subsystems.locomotion import MobilitySubsystem

__all__ = ["MobilitySubsystem"]

