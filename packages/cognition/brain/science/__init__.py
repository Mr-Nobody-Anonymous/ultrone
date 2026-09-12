# Copyright (c) Ultrone Contributors. All rights reserved.
"""AI Scientist — autonomous research hypothesis generation and evaluation.

This layer proposes and evaluates novel research ideas rather than just
implementing algorithms. It provides a self-driving research loop:

- ``Scientist``: Orchestrates the full research lifecycle
- ``HypothesisGenerator``: Proposes new research hypotheses
- ``NoveltyDetector``: Assesses the novelty of ideas against existing work
- ``ExperimentDesigner``: Designs rigorous experiments
- ``PublicationWriter``: Drafts research papers
- ``PeerReviewer``: Reviews papers for quality
- ``CitationNetwork``: Builds and analyzes citation graphs
"""

from .scientist import Scientist
from .hypothesis_generator import ScientistHypothesisGenerator
from .novelty_detector import NoveltyDetector
from .experiment_designer import ExperimentDesigner
from .publication_writer import PublicationWriter
from .peer_reviewer import PeerReviewer
from .citation_network import CitationNetwork

__all__ = [
    "Scientist",
    "ScientistHypothesisGenerator",
    "NoveltyDetector",
    "ExperimentDesigner",
    "PublicationWriter",
    "PeerReviewer",
    "CitationNetwork",
]
