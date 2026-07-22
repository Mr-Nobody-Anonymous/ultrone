# Copyright (c) Ultrone Contributors. All rights reserved.
"""Military configuration and doctrine presets."""

from .settings import MilitaryConfig
from .doctrine_presets import DoctrinePreset, DoctrineType, get_doctrine_preset

__all__ = ["MilitaryConfig", "DoctrinePreset", "DoctrineType", "get_doctrine_preset"]