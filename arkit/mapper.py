"""
arkit/mapper.py

ARKit → Rig Blendshape Mapper

This module provides the runtime engine that converts Apple ARKit 52
facial expression coefficients into target rig blendshape weights.
It supports mapping tables with multipliers, offsets, inversion,
clamping, mirroring, and normalization.

The mapper is Maya‑agnostic and produces normalized weight dictionaries
that can be consumed by any adapter (e.g., a Maya node interface).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Set, Union
from collections import defaultdict

# ---- Part 1: Foundation --------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# Constants
DEFAULT_MULTIPLIER = 1.0
DEFAULT_OFFSET = 0.0
DEFAULT_INVERT = False
DEFAULT_CLAMP_MIN = 0.0
DEFAULT_CLAMP_MAX = 1.0
DEFAULT_NORMALIZE = False

# Exceptions
class ARKitMapperError(Exception):
    """Base exception for mapper errors."""
    pass

class MappingDefinitionError(ARKitMapperError):
    """Raised when the mapping definition is invalid."""
    pass

class EvaluationError(ARKitMapperError):
    """Raised when frame evaluation fails."""
    pass

logger = logging.getLogger(__name__)

# ---- Part 2: Data Models ------------------------------------------------

@dataclass
class MappingRule:
    """
    A single mapping rule from one ARKit source to one rig target.
    """
    target: str
    multiplier: float = DEFAULT_MULTIPLIER
    offset: float = DEFAULT_OFFSET
    invert: bool = DEFAULT_INVERT
    clamp_min: float = DEFAULT_CLAMP_MIN
    clamp_max: float = DEFAULT_CLAMP_MAX

    def __post_init__(self):
        if self.multiplier == 0.0:
            logger.warning(f"Multiplier is zero for target '{self.target}' – rule will have no effect.")
        if self.clamp_min > self.clamp_max:
            raise ValueError(f"clamp_min ({self.clamp_min}) > clamp_max ({self.clamp_max})")

    def apply(self, value: float) -> float:
        """
        Apply this rule to an input ARKit value.
        Steps: invert -> multiplier -> offset -> clamp.
        """
        if self.invert:
            value = 1.0 - value
        value *= self.multiplier
        value += self.offset
        
        if value < self.clamp_min:
            value = self.clamp_min
        elif value > self.clamp_max:
            value = self.clamp_max
        return value


@dataclass
class CompiledSource:
    """
    Compiled rules for one ARKit source blendshape.
    Contains a list of MappingRule objects and a flag for quick skipping.
    """
    rules: List[MappingRule] = field(default_factory=list)
    is_empty: bool = True

    def add_rule(self, rule: MappingRule):
        self.rules.append(rule)
        if rule.multiplier != 0.0:
            self.is_empty = False


@dataclass
class CompiledMapping:
    """
    Fully compiled mapping from ARKit sources to rig targets.
    Also stores mirror mapping and normalization settings.
    """
    sources: Dict[str, CompiledSource] = field(default_factory=dict)
    mirror_map: Dict[str, str] = field(default_factory=dict)
    normalize: bool = DEFAULT_NORMALIZE
    pre_process: Optional[Callable[[Dict[str, float]], Dict[str, float]]] = None
    post_process: Optional[Callable[[Dict[str, float]], Dict[str, float]]] = None


@dataclass
class EvaluationResult:
    """
    Result of a single frame evaluation.
    Contains the computed weights and optional diagnostics.
    """
    weights: Dict[str, float]
    source_count: int = 0
    target_count: int = 0
    elapsed_time: float = 0.0
    warnings: List[str] = field(default_factory=list)

# ---- Part 3: Mapping Rules (Parser/Loader) ------------------------------

class MappingParser:
    """
    Parses a user‑friendly mapping definition into a CompiledMapping.
    """
    @staticmethod
    def parse(
        mapping_def: Dict[str, Union[List[Dict], Dict, str]],
        mirror_map: Optional[Dict[str, str]] = None,
        normalize: bool = DEFAULT_NORMALIZE,
        pre_process: Optional[Callable] = None,
        post_process: Optional[Callable] = None,
    ) -> CompiledMapping:
        """
        Parse a mapping definition dict into a compiled runtime-ready structure.
        """
        if not isinstance(mapping_def, dict):
            raise MappingDefinitionError("Mapping definition must be a dict")

        compiled = CompiledMapping(
            mirror_map=mirror_map or {},
            normalize=normalize,
            pre_process=pre_process,
            post_process=post_process,
        )

        for source, rules_data in mapping_def.items():
            if not isinstance(source, str) or not source:
                raise MappingDefinitionError(f"Source name must be a non‑empty string, got {source!r}")

            # Normalize structural shortcuts to a uniform list of dicts
            if isinstance(rules_data, str):
                normalized_rules = [{"target": rules_data}]
            elif isinstance(rules_data, dict):
                normalized_rules = [rules_data]
            elif isinstance(rules_data, list):
                if not rules_data:
                    continue
                normalized_rules = []
                for item in rules_data:
                    if isinstance(item, str):
                        normalized_rules.append({"target": item})
                    elif isinstance(item, dict):
                        normalized_rules.append(item)
                    else:
                        raise MappingDefinitionError(
                            f"Rule for source '{source}' must be str or dict, got {type(item).__name__}"
                        )
            else:
                raise MappingDefinitionError(
                    f"Invalid rules for source '{source}': expected str, dict, or list, got {type(rules_data).__name__}"
                )

            comp_source = CompiledSource()
            for rule_dict in normalized_rules:
                target = rule_dict.get("target")
                if not target or not isinstance(target, str):
                    raise MappingDefinitionError(
                        f"Rule for source '{source}' missing 'target' (string) field"
                    )
                
                rule = MappingRule(
                    target=target,
                    multiplier=float(rule_dict.get("multiplier", DEFAULT_MULTIPLIER)),
                    offset=float(rule_dict.get("offset", DEFAULT_OFFSET)),
                    invert=bool(rule_dict.get("invert", DEFAULT_INVERT)),
                    clamp_min=float(rule_dict.get("clamp_min", DEFAULT_CLAMP_MIN)),
                    clamp_max=float(rule_dict.get("clamp_max", DEFAULT_CLAMP_MAX)),
                )
                comp_source.add_rule(rule)

            if not comp_source.is_empty:
                compiled.sources[source] = comp_source

        return compiled

# ---- Part 4: Mapping Engine (Main Class) --------------------------------

class ARKitMapper:
    """
    The main mapper engine. Handles validation, mirroring, rule execution,
    and performance caching for evaluation sequences.
    """

    def __init__(
        self,
        mapping_def: Optional[Dict[str, Any]] = None,
        mirror_map: Optional[Dict[str, str]] = None,
        normalize: bool = DEFAULT_NORMALIZE,
        pre_process: Optional[Callable] = None,
        post_process: Optional[Callable] = None,
    ):
        self._compiled: Optional[CompiledMapping] = None
        self._diagnostics = DiagnosticsCollector()
        self._cache = EvaluationCache(maxsize=128)

        if mapping_def is not None:
            self.load(mapping_def, mirror_map, normalize, pre_process, post_process)

    def evaluate(self, frame: Dict[str, float]) -> EvaluationResult:
        """
        Evaluate a single frame (dict of ARKit coefficients) and return
        an EvaluationResult containing the rig weights.
        """
        if self._compiled is None:
            raise EvaluationError("No mapping loaded. Call load() first.")

        start_time = time.perf_counter()

        # --- Pre‑process ---
        if self._compiled.pre_process:
            try:
                frame = self._compiled.pre_process(frame)
            except Exception as e:
                logger.warning(f"Pre‑process hook failed: {e}")

        # --- Validate and clean input ---
        clamped_frame = {}
        for key, value in frame.items():
            if not isinstance(value, (int, float)):
                logger.warning(f"Non‑numeric value for '{key}': {value!r}, using 0.0")
                value = 0.0
            
            if value < 0.0:
                value = 0.0
            elif value > 1.0:
                value = 1.0
            clamped_frame[key] = value

        # --- Mirror missing values ---
        mirrored = dict(clamped_frame)
        mirror_map = self._compiled.mirror_map
        
        # Construct bidirectional lookup map to capture both directions
        all_pairs = {}
        for k, v in mirror_map.items():
            all_pairs[k] = v
            all_pairs[v] = k

        for source in self._compiled.sources.keys():
            if source not in mirrored:
                mirror_source = all_pairs.get(source)
                if mirror_source and mirror_source in mirrored:
                    mirrored[source] = mirrored[mirror_source]
                    logger.debug(f"Mirrored {mirror_source} -> {source}")

        # --- Performance Cache Evaluation Lookup ---
        # Generate hashable tuple representation of the inputs
        cache_key = frozenset(mirrored.items())
        cached_weights = self._cache.get(cache_key)
        if cached_weights is not None:
            elapsed = time.perf_counter() - start_time
            self._diagnostics.record_frame(len(mirrored), len(cached_weights), elapsed)
            return EvaluationResult(
                weights=dict(cached_weights),
                source_count=len(mirrored),
                target_count=len(cached_weights),
                elapsed_time=elapsed,
            )

        # --- Apply compiled rules ---
        target_weights: Dict[str, float] = defaultdict(float)

        for source, comp_source in self._compiled.sources.items():
            value = mirrored.get(source, 0.0)
            for rule in comp_source.rules:
                target_weights[rule.target] += rule.apply(value)

        # --- Normalize ---
        if self._compiled.normalize:
            total = sum(target_weights.values())
            if total > 1e-12:
                for key in target_weights:
                    target_weights[key] /= total

        # --- Post‑process ---
        if self._compiled.post_process:
            try:
                target_weights = self._compiled.post_process(dict(target_weights))
            except Exception as e:
                logger.warning(f"Post‑process hook failed: {e}")

        # Final conversions & clean cast from defaultdict
        final_weights = dict(target_weights)
        
        # Populate performance caching framework
        self._cache.put(cache_key, final_weights)

        elapsed = time.perf_counter() - start_time
        self._diagnostics.record_frame(len(mirrored), len(final_weights), elapsed)

        return EvaluationResult(
            weights=final_weights,
            source_count=len(mirrored),
            target_count=len(final_weights),
            elapsed_time=elapsed,
        )

    def evaluate_batch(self, frames: List[Dict[str, float]]) -> List[EvaluationResult]:
        """
        Evaluate multiple frames in batch sequence.
        """
        return [self.evaluate(frame) for frame in frames]

    def get_diagnostics(self) -> Dict[str, Any]:
        return self._diagnostics.get_stats()

    def reset_diagnostics(self):
        self._diagnostics.reset()

    def statistics(self) -> Dict[str, Any]:
        """
        Return summary statistics about the loaded mapping architecture.
        """
        if self._compiled is None:
            return {"loaded": False}

        total_sources = len(self._compiled.sources)
        total_targets = sum(len(src.rules) for src in self._compiled.sources.values())
        
        unique_targets = set()
        for src in self._compiled.sources.values():
            for rule in src.rules:
                unique_targets.add(rule.target)

        return {
            "loaded": True,
            "source_count": total_sources,
            "total_rule_count": total_targets,
            "unique_target_count": len(unique_targets),
            "mirror_pairs": len(self._compiled.mirror_map),
            "normalize": self._compiled.normalize,
            "has_pre_process": self._compiled.pre_process is not None,
            "has_post_process": self._compiled.post_process is not None,
        }

    def load(
        self,
        mapping_def: Dict[str, Any],
        mirror_map: Optional[Dict[str, str]] = None,
        normalize: bool = DEFAULT_NORMALIZE,
        pre_process: Optional[Callable] = None,
        post_process: Optional[Callable] = None,
    ) -> None:
        """
        Load a new mapping definition, replacing any existing execution maps.
        """
        self._compiled = MappingParser.parse(
            mapping_def,
            mirror_map=mirror_map,
            normalize=normalize,
            pre_process=pre_process,
            post_process=post_process,
        )
        self._cache.clear()
        self.reset_diagnostics()
        logger.info(f"Loaded mapping with {len(self._compiled.sources)} sources.")

    def clear(self) -> None:
        """Clear the loaded mapping and reset diagnostics/caches."""
        self._compiled = None
        self._cache.clear()
        self.reset_diagnostics()

    @property
    def is_loaded(self) -> bool:
        return self._compiled is not None

# ---- Diagnostics Collector ---------------------------------------------

class DiagnosticsCollector:
    def __init__(self):
        self.reset()

    def reset(self):
        self.frame_count = 0
        self.total_source_count = 0
        self.total_target_count = 0
        self.total_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0

    def record_frame(self, source_count: int, target_count: int, elapsed: float):
        self.frame_count += 1
        self.total_source_count += source_count
        self.total_target_count += target_count
        self.total_time += elapsed
        if elapsed < self.min_time:
            self.min_time = elapsed
        if elapsed > self.max_time:
            self.max_time = elapsed

    def get_stats(self) -> Dict[str, Any]:
        if self.frame_count == 0:
            return {
                "frame_count": 0,
                "avg_time": 0.0,
                "min_time": 0.0,
                "max_time": 0.0,
                "avg_sources": 0.0,
                "avg_targets": 0.0,
            }
        return {
            "frame_count": self.frame_count,
            "avg_time": self.total_time / self.frame_count,
            "min_time": self.min_time if self.min_time != float('inf') else 0.0,
            "max_time": self.max_time,
            "avg_sources": self.total_source_count / self.frame_count,
            "avg_targets": self.total_target_count / self.frame_count,
        }

# ---- Evaluation Cache (LRU implementation) ---------------------------

class EvaluationCache:
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: Dict[frozenset, Dict[str, float]] = {}
        self._order: List[frozenset] = []

    def get(self, key: frozenset) -> Optional[Dict[str, float]]:
        if key in self._cache:
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        return None

    def put(self, key: frozenset, value: Dict[str, float]):
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self.maxsize:
            oldest = self._order.pop(0)
            del self._cache[oldest]
        self._cache[key] = value
        self._order.append(key)

    def clear(self):
        self._cache.clear()
        self._order.clear()

# ---- Public API --------------------------------------------------------

__all__ = [
    "ARKitMapper",
    "MappingRule",
    "CompiledSource",
    "CompiledMapping",
    "EvaluationResult",
    "ARKitMapperError",
    "MappingDefinitionError",
    "EvaluationError",
    "MappingParser",
]