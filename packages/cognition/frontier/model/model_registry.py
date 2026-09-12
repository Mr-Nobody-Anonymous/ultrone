# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model registry — manages model configurations and instances.

Provides a registry for registering, building, and retrieving models and
their configurations. Supports both experimental local models and external
pretrained models via backend adapters.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base_model import BaseModel, create_model
from .model_config import ModelConfig

logger = logging.getLogger("Ultrone.Frontier.Model.Registry")


@dataclass
class ModelRecord:
    """A record in the model registry."""

    model_id: str
    config: Dict[str, Any]
    backend: str
    status: str = "registered"  # registered, built, failed
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "config": self.config,
            "backend": self.backend,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class ModelRegistry:
    """Central registry for models and configurations.

    Supports:
    - Registering model configurations
    - Registering pre-built model instances
    - Building models from registered configs
    - Retrieving models by ID
    - Listing all registered models
    """

    def __init__(self):
        self._records: Dict[str, ModelRecord] = {}
        self._instances: Dict[str, BaseModel] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_config(
        self,
        model_id: str,
        backend: str,
        config: Optional[ModelConfig] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelRecord:
        """Register a model configuration.

        Parameters
        ----------
        model_id : str
            Unique identifier for the model.
        backend : str
            Backend name ("rule", "mock", "huggingface", "vllm", "llamacpp").
        config : Optional[ModelConfig]
            Local model configuration (for TransformerModel).
        config_dict : Optional[Dict[str, Any]]
            Backend-specific configuration dict.
        metadata : Optional[Dict[str, Any]]
            Additional metadata.

        Returns
        -------
        ModelRecord
            The created record.
        """
        record = ModelRecord(
            model_id=model_id,
            backend=backend,
            config=config.to_dict() if config else (config_dict or {}),
            metadata=metadata or {},
            status="registered",
        )
        self._records[model_id] = record
        logger.info("Registered model config '%s' (backend=%s)", model_id, backend)
        return record

    def register_instance(
        self,
        model: BaseModel,
        model_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelRecord:
        """Register a pre-built model instance.

        Parameters
        ----------
        model : BaseModel
            The model instance to register.
        model_id : Optional[str]
            Override the model ID (defaults to model.model_id).
        metadata : Optional[Dict[str, Any]]
            Additional metadata.

        Returns
        -------
        ModelRecord
            The created record.
        """
        mid = model_id or model.model_id
        record = ModelRecord(
            model_id=mid,
            backend=model.__class__.__name__,
            config={},
            status="built",
            metadata=metadata or {},
        )
        self._records[mid] = record
        self._instances[mid] = model
        return record

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------
    def build(self, model_id: str, **build_kwargs: Any) -> BaseModel:
        """Build a model from a registered configuration.

        Parameters
        ----------
        model_id : str
            The model ID to build.
        **build_kwargs
            Additional kwargs passed to the backend.

        Returns
        -------
        BaseModel
            The built model.
        """
        record = self._records.get(model_id)
        if record is None:
            raise KeyError(f"Model '{model_id}' not found in registry")

        try:
            if record.backend in ("rule", "rules", "rule-based"):
                from .base_model import RuleBasedModel

                model = RuleBasedModel(model_id=model_id)
            elif record.backend in ("mock", "mock-model"):
                from .base_model import MockModel

                model = MockModel(model_id=model_id, **record.config)
            elif record.backend in ("huggingface", "hf", "transformers"):
                model = create_model(
                    record.backend,
                    model_name=record.config.get("model_name"),
                    model_id=model_id,
                    **build_kwargs,
                )
            elif record.backend in ("vllm", "vllm-engine"):
                model = create_model(
                    record.backend,
                    model_name=record.config.get("model_name"),
                    model_id=model_id,
                    **build_kwargs,
                )
            elif record.backend in ("llamacpp", "llama.cpp", "gguf"):
                model = create_model(
                    record.backend,
                    model_path=record.config.get("model_path"),
                    model_id=model_id,
                    **build_kwargs,
                )
            else:
                # Unknown backend: create via create_model
                model = create_model(record.backend, model_id=model_id, **build_kwargs)

            self._instances[model_id] = model
            record.status = "built"
            logger.info("Built model '%s'", model_id)
            return model
        except Exception as exc:
            record.status = "failed"
            record.metadata["error"] = str(exc)
            raise

    def build_local_transformer(self, model_id: str, config: ModelConfig) -> BaseModel:
        """Build a local transformer model from a config.

        Registers the config and builds a TransformerModel wrapped in a
        BaseModel-compatible interface.

        Parameters
        ----------
        model_id : str
            Model ID.
        config : ModelConfig
            The model configuration.

        Returns
        -------
        BaseModel
            A BaseModel-compatible wrapper.
        """
        from .transformer import TransformerModel

        record = self.register_config(model_id, "local_transformer", config=config)
        transformer = TransformerModel(config)
        model = LocalTransformerWrapper(model_id, transformer, config)
        self._instances[model_id] = model
        record.status = "built"
        return model

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def get(self, model_id: str) -> Optional[BaseModel]:
        """Get a built model instance by ID."""
        return self._instances.get(model_id)

    def get_record(self, model_id: str) -> Optional[ModelRecord]:
        """Get a model record by ID."""
        return self._records.get(model_id)

    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        return [r.to_dict() for r in self._records.values()]

    def list_ids(self) -> List[str]:
        """List all registered model IDs."""
        return list(self._records.keys())

    def remove(self, model_id: str) -> bool:
        """Remove a model from the registry."""
        existed = model_id in self._records
        self._records.pop(model_id, None)
        self._instances.pop(model_id, None)
        return existed

    def get_stats(self) -> Dict[str, Any]:
        """Return registry statistics."""
        return {
            "type": "ModelRegistry",
            "registered": len(self._records),
            "built": len(self._instances),
            "models": self.list_models(),
        }


class LocalTransformerWrapper(BaseModel):
    """Wraps a local TransformerModel in the BaseModel interface."""

    def __init__(self, model_id: str, transformer: Any, config: ModelConfig):
        super().__init__(model_id)
        self.transformer = transformer
        self.config = config

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text.

        Note: This requires a tokenizer. For direct use, the prompt is
        treated as a sequence ID when possible.
        """
        # For a local transformer without a tokenizer, return a stats summary.
        # Real generation requires a tokenizer adapter.
        return f"[LocalTransformer {self.model_id}: {self.transformer.get_num_parameters()} parameters]"

    def get_stats(self) -> Dict[str, Any]:
        """Return model statistics."""
        stats = self._base_stats()
        stats.update(self.transformer.get_stats())
        return stats


def get_model_registry() -> ModelRegistry:
    """Get the global model registry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ModelRegistry()
    return _GLOBAL_REGISTRY


_GLOBAL_REGISTRY: Optional[ModelRegistry] = None