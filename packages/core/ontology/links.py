# Copyright (c) Ultrone Contributors. All rights reserved.
"""Typed Ontology Links connecting semantic objects."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class OntologyLink:
    source_id: str
    target_id: str
    relation_type: str       # 'observes', 'communicates_with', 'located_in', 'derived_from', 'protects', 'threatens'
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
