from enum import Enum
import logging
from typing import Any

class ClassificationLevel(Enum):
    UNCLASSIFIED = 1
    CONFIDENTIAL = 2
    SECRET = 3
    TOP_SECRET = 4

class MilitaryLogger:
    def __init__(self, name: str, level: ClassificationLevel = ClassificationLevel.UNCLASSIFIED):
        self.logger = logging.getLogger(f"Ultrone.{name}")
        self.level = level
    
    def log(self, message: str, classification: ClassificationLevel = ClassificationLevel.UNCLASSIFIED) -> None:
        if classification.value <= self.level.value:
            self.logger.info(message)