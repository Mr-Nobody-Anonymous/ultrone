"""Meta-Learning & Continual Learning module.

Provides algorithms for learning to learn and adapting to new tasks:

- ``BaseMetaLearner``: Abstract interface for meta-learning algorithms
- ``MAML``: Model-Agnostic Meta-Learning
- ``Reptile``: First-order meta-learning
- ``TransferLearning``: Transfer learning and domain adaptation
- ``OnlineLearning``: Online learning algorithms
- ``ContinualLearning``: Continual/lifelong learning
- ``KnowledgeDistillation``: Model compression via distillation
"""

from .base import BaseMetaLearner, MetaLearningConfig, MetaTask
from .maml import MAML, MAMLConfig
from .reptile import Reptile, ReptileConfig
from .transfer_learning import TransferLearning, TransferConfig
from .online_learning import OnlineLearning, OnlineConfig
from .continual_learning import ContinualLearning, ContinualConfig
from .knowledge_distillation import KnowledgeDistillation, DistillConfig

__all__ = [
    "BaseMetaLearner", "MetaLearningConfig", "MetaTask",
    "MAML", "MAMLConfig",
    "Reptile", "ReptileConfig",
    "TransferLearning", "TransferConfig",
    "OnlineLearning", "OnlineConfig",
    "ContinualLearning", "ContinualConfig",
    "KnowledgeDistillation", "DistillConfig",
]

