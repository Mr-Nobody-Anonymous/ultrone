# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE Ontology Package.

Re-exports core ontology constructs: OntologyObject, OntologyLink, OntologyAction.
"""
from packages.core.ontology.objects import (
    OntologyObject,
    OntologyLink,
    OntologyAction,
)

__all__ = [
    "OntologyObject",
    "OntologyLink",
    "OntologyAction",
]
