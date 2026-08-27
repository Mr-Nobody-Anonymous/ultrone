# Copyright (c) Ultrone Contributors. All rights reserved.
"""Typed parameter registry with bounds, versions, and dependencies.

Every tunable knob in ULTRONE is declared here -- name, type, value,
bounds, default, version, dependencies, and the evaluation metric it is
expected to influence. Nothing may set a value that is undeclared,
out-of-bounds, or type-mismatched: adaptation happens THROUGH this
registry or not at all, which is what makes sandboxed experimentation
safe (candidates are just alternative snapshots of this registry).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

_PARAM_TYPES = ("float", "int", "bool", "str")


@dataclass(frozen=True)
class ParameterSpec:
    """Declaration of one tunable parameter."""

    name: str
    type: str                          # float | int | bool | str
    default: Any
    bounds: Optional[Tuple[float, float]] = None   # numeric only
    choices: Optional[Tuple[str, ...]] = None      # str only
    version: int = 1
    dependencies: Tuple[str, ...] = ()
    metric: str = ""                   # evaluation metric influenced
    description: str = ""

    def validate_type(self, value: Any) -> bool:
        if self.type == "float":
            return isinstance(value, (int, float)) \
                and not isinstance(value, bool)
        if self.type == "int":
            return isinstance(value, int) and not isinstance(value, bool)
        if self.type == "bool":
            return isinstance(value, bool)
        return isinstance(value, str)


class ParameterRegistry:
    """Authoritative store of every declared parameter and its value."""

    def __init__(self) -> None:
        self._specs: Dict[str, ParameterSpec] = {}
        self._values: Dict[str, Any] = {}
        self._version_counter: Dict[str, int] = {}

    # -- declaration ----------------------------------------------------- #
    def declare(
        self,
        name: str,
        type_: str,
        default: Any,
        bounds: Optional[Tuple[float, float]] = None,
        choices: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        metric: str = "",
        description: str = "",
    ) -> ParameterSpec:
        if type_ not in _PARAM_TYPES:
            raise ValueError(f"unknown parameter type '{type_}'")
        if name in self._specs:
            raise ValueError(f"parameter '{name}' already declared")
        spec = ParameterSpec(
            name=name, type=type_, default=default,
            bounds=tuple(bounds) if bounds else None,
            choices=tuple(choices) if choices else None,
            dependencies=tuple(dependencies or ()),
            metric=metric, description=description,
        )
        if spec.bounds is not None:
            if spec.type not in ("float", "int"):
                raise ValueError("bounds apply to numeric parameters only")
            lo, hi = spec.bounds
            if lo > hi:
                raise ValueError(f"invalid bounds for '{name}'")
        value = self._coerce(spec, default)
        for dep in spec.dependencies:
            if dep not in self._specs and dep != name:
                raise ValueError(
                    f"parameter '{name}' depends on undeclared '{dep}'")
        self._specs[name] = spec
        self._values[name] = value
        self._version_counter[name] = 1
        return spec

    # -- access ------------------------------------------------------------ #
    def names(self) -> List[str]:
        return sorted(self._specs)

    def spec(self, name: str) -> ParameterSpec:
        return self._specs[name]

    def get(self, name: str) -> Any:
        return self._values[name]

    def branch(self, group: str) -> Dict[str, Any]:
        """Parameters whose dotted name starts with ``group``."""
        prefix = group + "."
        return {n: v for n, v in self._values.items()
                if n.startswith(prefix)}

    # -- mutation ------------------------------------------------------------ #
    def set(self, name: str, value: Any) -> Any:
        """Set one parameter; returns the stored (coerced/clamped) value."""
        spec = self._specs.get(name)
        if spec is None:
            raise KeyError(f"undeclared parameter '{name}'")
        coerced = self._coerce(spec, value)
        previous = self._values[name]
        self._values[name] = coerced
        if coerced != previous:
            self._version_counter[name] += 1
        return coerced

    def apply_overrides(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Apply candidate values; rejects unknown names up-front."""
        for name in overrides:
            if name not in self._specs:
                raise KeyError(f"undeclared parameter '{name}'")
        return {name: self.set(name, value)
                for name, value in overrides.items()}

    def apply(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Canonical bulk-load entry point (alias of ``apply_overrides``).

        Used when flowing a stored configuration (e.g. the BrainStore
        ``production`` channel) back into a fresh registry for the next
        episode -- the step that closes the learning loop. Bounds and
        type enforcement come from ``set`` exactly as for single keys.
        """
        return self.apply_overrides(overrides)

    def reset(self, name: Optional[str] = None) -> None:
        targets = [name] if name else self.names()
        for target in targets:
            self.set(target, self._specs[target].default)

    # -- snapshots --------------------------------------------------------------- #
    def snapshot(self) -> Dict[str, Any]:
        return {n: self._values[n] for n in self.names()}

    def config_hash(self) -> str:
        # NOTE: default json separators -- must stay byte-identical to
        # adaptive.optimizer.config_hash for the same mapping.
        payload = json.dumps(self.snapshot(), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def export(self) -> Dict[str, Any]:
        return {
            "config_hash": self.config_hash(),
            "parameters": {
                n: {"type": s.type,
                    "value": self._values[n],
                    "default": s.default,
                    "bounds": list(s.bounds) if s.bounds else None,
                    "version": self._version_counter[n],
                    "metric": s.metric}
                for n, s in ((n, self._specs[n]) for n in self.names())
            },
        }

    @classmethod
    def from_snapshot(cls, parameters: Dict[str, Any]) -> "ParameterRegistry":
        """Rebuild a registry from ``export()['parameters']`` shape."""
        registry = cls()
        for name, meta in sorted(parameters.items()):
            bounds = meta.get("bounds")
            registry.declare(
                name=name,
                type_=meta["type"],
                default=meta["default"],
                bounds=(bounds[0], bounds[1])
                if isinstance(bounds, (list, tuple)) and len(bounds) == 2
                else None,
                metric=meta.get("metric", ""),
            )
            if meta["value"] != meta["default"]:
                registry.set(name, meta["value"])
        return registry

    # -- internal ------------------------------------------------------------------ #
    def _coerce(self, spec: ParameterSpec, value: Any) -> Any:
        if spec.type == "int" and isinstance(value, (int, float)) \
                and not isinstance(value, bool):
            # Optimizer proposals may arrive as floats -- round, don't
            # reject; bounds clamp AFTER rounding.
            rounded = int(round(float(value)))
            if spec.bounds is not None:
                lo, hi = spec.bounds
                rounded = min(hi, max(lo, rounded))
            if spec.choices is not None and rounded not in spec.choices:
                raise ValueError(
                    f"value {rounded!r} not in choices {spec.choices}")
            return rounded
        if not spec.validate_type(value):
            raise TypeError(
                f"parameter '{spec.name}' expects {spec.type}, "
                f"got {type(value).__name__}")
        if spec.bounds is not None:
            lo, hi = spec.bounds
            value = min(hi, max(lo, float(value)))
        if spec.choices is not None and value not in spec.choices:
            raise ValueError(
                f"value {value!r} not in choices {list(spec.choices)}")
        return value