"""
arkit/remapper.py

ARKit Mapping Remapper

This module transforms one ARKit mapping definition into another.
It handles renaming, mirroring, merging, splitting, and filtering of
mapping tables that define relationships between ARKit blendshape
coefficients and rig target attributes.

The remapper is the counterpart to mapper.py:
    mapper.py:   ARKit coefficients → rig weights
    remapper.py: Mapping A → Mapping B

This is essential for converting between different rig naming conventions,
migrating presets, adapting to new face rigs, and enabling interoperability
across facial animation ecosystems.

Responsibilities
----------------
• Rename blendshapes (simple, pattern-based, or with a callback)
• Convert naming conventions (e.g., CamelCase, snake_case, prefixes)
• Mirror mappings using left/right symmetry from arkit52.py
• Merge multiple mappings (sum or average)
• Split a mapping into sub‑mappings (by region, category, or custom filter)
• Filter mappings by source or target names
• Batch‑convert multiple mappings (e.g., entire preset library)
• Provide detailed diagnostics and statistics

Architecture
------------
Foundation (imports, constants, exceptions, logging)
↓
Data Models (RenameRule, MirrorRule, RemapRule, MergeRule, SplitRule,
             RemapResult, RemapStatistics)
↓
Rename Rules Engine
↓
Mapping Conversion Engine (core remap logic)
↓
Mirroring Engine
↓
Filtering & Selection
↓
Merge & Split Operations
↓
Batch Remapping
↓
Diagnostics
↓
Statistics
↓
Public API (ARKitRemapper)

Examples
--------
    remapper = ARKitRemapper()
    
    # Simple rename dictionary
    rename_map = {"Smile_L": "mouthSmileLeft"}
    new_mapping = remapper.remap(mapping, rename_map=rename_map)
    
    # Mirror a mapping (swap left/right)
    mirrored = remapper.mirror(mapping)
    
    # Filter to only mouth channels
    filtered = remapper.filter(mapping, sources=["mouthSmileLeft", "mouthFrownLeft", ...])
    
    # Merge two mappings (sum)
    merged = remapper.merge(mapping1, mapping2, operation="sum")
    
    # Split by region
    parts = remapper.split(mapping, by="region")  # returns dict of region->mapping
"""

from __future__ import annotations

import copy
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Union, Callable, Iterable

# Import ARKit constants from the canonical module
try:
    from .arkit52 import ARKIT_BLENDSHAPES, ARKIT_SET, LEFT_RIGHT_PAIRS, FACIAL_REGIONS, EXPRESSION_CATEGORIES
except ImportError:
    # Fallback definitions (should not happen in production)
    ARKIT_BLENDSHAPES = []
    ARKIT_SET = set()
    LEFT_RIGHT_PAIRS = {}
    FACIAL_REGIONS = {}
    EXPRESSION_CATEGORIES = {}

# Import validator to ensure consistency
try:
    from .validator import ARKitValidator, ValidationLevel
except ImportError:
    # Fallback dummy validator for development
    class ARKitValidator:
        def validate_mapping(self, mapping, level=None, **kwargs):
            from dataclasses import dataclass
            @dataclass
            class DummyReport:
                is_valid = True
                errors = []
                warnings = []
            return DummyReport()
    ValidationLevel = None

# ---- Part 1: Foundation --------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class ARKitRemapperError(Exception):
    """Base exception for remapper errors."""
    pass

class RemapDefinitionError(ARKitRemapperError):
    """Raised when remap rules are invalid."""
    pass

class RemapOperationError(ARKitRemapperError):
    """Raised when a remap operation fails."""
    pass


# ---- Part 2: Data Models ------------------------------------------------

@dataclass
class RenameRule:
    """
    Defines how to rename a source or target channel.
    """
    # One of the following should be provided:
    mapping: Optional[Dict[str, str]] = None       # explicit dict {old_name: new_name}
    pattern: Optional[str] = None                  # regex pattern for matching
    replacement: Optional[str] = None              # replacement string (can use backreferences)
    case: Optional[str] = None                     # 'upper', 'lower', 'title', 'camel', 'snake'
    prefix: Optional[str] = None                   # add prefix
    suffix: Optional[str] = None                   # add suffix
    remove_prefix: Optional[str] = None            # remove prefix
    remove_suffix: Optional[str] = None            # remove suffix
    callback: Optional[Callable[[str], str]] = None # arbitrary function

    def __post_init__(self):
        # Ensure at least one transformation is defined.
        if not any([
            self.mapping, self.pattern, self.case, self.prefix, self.suffix,
            self.remove_prefix, self.remove_suffix, self.callback
        ]):
            raise RemapDefinitionError("RenameRule must specify at least one transformation method.")

        # If pattern is given, replacement must be provided (unless callback handles it)
        if self.pattern and not self.replacement and not self.callback:
            raise RemapDefinitionError("If pattern is specified, replacement or callback must be provided.")

    def apply(self, name: str) -> str:
        """Apply the rename rule to a single name."""
        result = name

        # 1. Explicit mapping
        if self.mapping:
            result = self.mapping.get(name, result)

        # 2. Pattern substitution
        if self.pattern and self.replacement:
            try:
                result = re.sub(self.pattern, self.replacement, result)
            except Exception as e:
                logger.warning(f"Pattern substitution failed for '{name}': {e}")

        # 3. Remove prefix/suffix
        if self.remove_prefix and result.startswith(self.remove_prefix):
            result = result[len(self.remove_prefix):]
        if self.remove_suffix and result.endswith(self.remove_suffix):
            result = result[:-len(self.remove_suffix)]

        # 4. Case conversion
        if self.case:
            if self.case == 'upper':
                result = result.upper()
            elif self.case == 'lower':
                result = result.lower()
            elif self.case == 'title':
                result = result.title()
            elif self.case == 'camel':
                # Convert snake or spaced to camelCase
                parts = re.split(r'[_\s]+', result)
                result = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])
            elif self.case == 'snake':
                # Convert camel to snake
                result = re.sub(r'(?<!^)(?=[A-Z])', '_', result).lower()
            # Other cases could be added.

        # 5. Add prefix/suffix
        if self.prefix:
            result = self.prefix + result
        if self.suffix:
            result = result + self.suffix

        # 6. Callback (last to override)
        if self.callback:
            result = self.callback(result)

        return result


@dataclass
class MirrorRule:
    """
    Defines how to mirror a mapping using left/right symmetry.
    """
    # Use the global LEFT_RIGHT_PAIRS from arkit52.py by default.
    pair_map: Optional[Dict[str, str]] = None
    # Optionally, specify patterns to detect left/right suffixes.
    left_pattern: Optional[str] = None
    right_pattern: Optional[str] = None

    def __post_init__(self):
        if self.pair_map is None:
            self.pair_map = LEFT_RIGHT_PAIRS
        if self.left_pattern is None:
            self.left_pattern = r'(?i)(Left|L|_L)$'
        if self.right_pattern is None:
            self.right_pattern = r'(?i)(Right|R|_R)$'

    def get_mirror(self, name: str) -> Optional[str]:
        """Return the mirror of a channel name, if known."""
        # First, check explicit pair map
        if name in self.pair_map:
            return self.pair_map[name]
        # Try pattern-based
        # If it ends with left pattern, replace with right pattern
        if re.search(self.left_pattern, name):
            # Remove the pattern and add right equivalent
            base = re.sub(self.left_pattern, '', name)
            # Try to find a right suffix in pair_map? or just replace.
            # Simple: replace 'Left' with 'Right' or 'L' with 'R'
            # We'll do a simple replacement based on common patterns.
            # Better: use the pair_map if we have it.
            # We'll just try to swap suffix.
            left_suffixes = ['Left', 'L', '_L']
            right_suffixes = ['Right', 'R', '_R']
            for ls, rs in zip(left_suffixes, right_suffixes):
                if name.endswith(ls):
                    return name[:-len(ls)] + rs
            # Also handle _L
        elif re.search(self.right_pattern, name):
            # Mirror reverse
            base = re.sub(self.right_pattern, '', name)
            for rs, ls in zip(['Right', 'R', '_R'], ['Left', 'L', '_L']):
                if name.endswith(rs):
                    return name[:-len(rs)] + ls
        return None


@dataclass
class RemapResult:
    """
    Result of a remap operation.
    """
    mapping: Dict[str, Any]          # The resulting mapping
    renamed_sources: Dict[str, str]  # old -> new for sources
    renamed_targets: Dict[str, str]  # old -> new for targets
    mirrored_sources: Dict[str, str] # source mirror mappings applied
    mirrored_targets: Dict[str, str] # target mirror mappings applied
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class RemapStatistics:
    """
    Statistics for a remap operation or batch.
    """
    total_sources_processed: int = 0
    total_targets_processed: int = 0
    renamed_sources: int = 0
    renamed_targets: int = 0
    mirrored_sources: int = 0
    mirrored_targets: int = 0
    merged_mappings: int = 0
    split_parts: int = 0
    removed_sources: int = 0
    removed_targets: int = 0
    errors: int = 0
    warnings: int = 0
    elapsed_ms: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


# ---- Part 3: Rename Rules Engine ----------------------------------------

class RenameEngine:
    """
    Applies a set of rename rules to source and target names in a mapping.
    """
    def __init__(self, rules: List[RenameRule]):
        self.rules = rules

    def apply_to_name(self, name: str) -> str:
        """Apply all rules in order to a single name."""
        result = name
        for rule in self.rules:
            result = rule.apply(result)
        return result

    def apply_to_mapping(
        self,
        mapping: Dict[str, Any],
        apply_to_sources: bool = True,
        apply_to_targets: bool = True,
    ) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str]]:
        """
        Apply rename rules to the mapping.

        Returns:
            (new_mapping, renamed_sources_map, renamed_targets_map)
        """
        new_mapping = {}
        renamed_sources = {}
        renamed_targets = {}

        for source, rules_data in mapping.items():
            new_source = source
            if apply_to_sources:
                new_source = self.apply_to_name(source)
                if new_source != source:
                    renamed_sources[source] = new_source

            # Process rules_data (list of rule dicts)
            if isinstance(rules_data, str):
                # simple target name
                new_target = rules_data
                if apply_to_targets:
                    new_target = self.apply_to_name(rules_data)
                    if new_target != rules_data:
                        renamed_targets[rules_data] = new_target
                # Build new rule: target string
                new_mapping[new_source] = new_target
            elif isinstance(rules_data, dict):
                # single rule dict
                new_target = rules_data.get("target", "")
                if apply_to_targets and new_target:
                    new_target_renamed = self.apply_to_name(new_target)
                    if new_target_renamed != new_target:
                        renamed_targets[new_target] = new_target_renamed
                    # copy other fields
                    new_rule = rules_data.copy()
                    new_rule["target"] = new_target_renamed
                    new_mapping[new_source] = new_rule
                else:
                    new_mapping[new_source] = rules_data
            elif isinstance(rules_data, list):
                # list of rule dicts
                new_rules = []
                for rule_dict in rules_data:
                    if isinstance(rule_dict, dict) and "target" in rule_dict:
                        old_target = rule_dict["target"]
                        if apply_to_targets:
                            new_target = self.apply_to_name(old_target)
                            if new_target != old_target:
                                renamed_targets[old_target] = new_target
                        else:
                            new_target = old_target
                        new_rule = rule_dict.copy()
                        new_rule["target"] = new_target
                        new_rules.append(new_rule)
                    else:
                        # If not a dict with target, just keep
                        new_rules.append(rule_dict)
                new_mapping[new_source] = new_rules
            else:
                # Unknown type, keep as is
                new_mapping[new_source] = rules_data

        return new_mapping, renamed_sources, renamed_targets


# ---- Part 4: Mapping Conversion Engine ---------------------------------

class MappingConverter:
    """
    Core conversion engine that applies renaming and mirroring to a mapping.
    """
    def __init__(self, rename_rules: Optional[List[RenameRule]] = None):
        self._rename_engine = RenameEngine(rename_rules or [])

    def convert(
        self,
        mapping: Dict[str, Any],
        rename_sources: bool = True,
        rename_targets: bool = True,
        mirror: bool = False,
        mirror_rule: Optional[MirrorRule] = None,
        validate: bool = True,
    ) -> RemapResult:
        """
        Convert a mapping by applying rename rules and optionally mirroring.
        """
        result = RemapResult(
            mapping={},
            renamed_sources={},
            renamed_targets={},
            mirrored_sources={},
            mirrored_targets={}
        )

        # 1. Apply renaming (if any)
        new_mapping, renamed_sources, renamed_targets = self._rename_engine.apply_to_mapping(
            mapping, rename_sources, rename_targets
        )
        result.renamed_sources = renamed_sources
        result.renamed_targets = renamed_targets
        result.mapping = new_mapping

        # 2. Apply mirroring (if requested)
        if mirror:
            mirrored = self._apply_mirror(new_mapping, mirror_rule)
            # Merge mirroring results
            result.mapping = mirrored["mapping"]
            result.mirrored_sources.update(mirrored["mirrored_sources"])
            result.mirrored_targets.update(mirrored["mirrored_targets"])

        # 3. Optional validation (using validator)
        if validate:
            try:
                val = ARKitValidator()
                report = val.validate_mapping(result.mapping, level=ValidationLevel.STANDARD if ValidationLevel else None)
                if not report.is_valid:
                    result.errors.extend([issue.message for issue in report.errors])
                result.warnings.extend([issue.message for issue in report.warnings])
            except Exception as e:
                result.errors.append(f"Validation error: {e}")

        return result

    def _apply_mirror(
        self,
        mapping: Dict[str, Any],
        mirror_rule: Optional[MirrorRule] = None
    ) -> Dict[str, Any]:
        """
        Mirror a mapping: swap left and right channels in both sources and targets.
        Returns dict with 'mapping', 'mirrored_sources', 'mirrored_targets'.
        """
        if mirror_rule is None:
            mirror_rule = MirrorRule()

        mirrored_sources = {}
        mirrored_targets = {}
        new_mapping = {}

        for source, rules_data in mapping.items():
            # Mirror source
            new_source = mirror_rule.get_mirror(source)
            if new_source and new_source != source:
                mirrored_sources[source] = new_source
            else:
                new_source = source  # no mirror or same

            # Process rules_data
            if isinstance(rules_data, str):
                # simple target
                new_target = mirror_rule.get_mirror(rules_data)
                if new_target and new_target != rules_data:
                    mirrored_targets[rules_data] = new_target
                else:
                    new_target = rules_data
                new_mapping[new_source] = new_target
            elif isinstance(rules_data, dict):
                # single rule dict
                old_target = rules_data.get("target", "")
                new_target = mirror_rule.get_mirror(old_target) if old_target else old_target
                if new_target and new_target != old_target:
                    mirrored_targets[old_target] = new_target
                else:
                    new_target = old_target
                new_rule = rules_data.copy()
                new_rule["target"] = new_target
                new_mapping[new_source] = new_rule
            elif isinstance(rules_data, list):
                # list of rules
                new_rules = []
                for rule_dict in rules_data:
                    if isinstance(rule_dict, dict) and "target" in rule_dict:
                        old_target = rule_dict["target"]
                        new_target = mirror_rule.get_mirror(old_target)
                        if new_target and new_target != old_target:
                            mirrored_targets[old_target] = new_target
                        else:
                            new_target = old_target
                        new_rule = rule_dict.copy()
                        new_rule["target"] = new_target
                        new_rules.append(new_rule)
                    else:
                        new_rules.append(rule_dict)
                new_mapping[new_source] = new_rules
            else:
                # keep as is
                new_mapping[new_source] = rules_data

        return {
            "mapping": new_mapping,
            "mirrored_sources": mirrored_sources,
            "mirrored_targets": mirrored_targets,
        }


# ---- Part 5: Mirroring Engine (already integrated) ---------------------

# The mirroring is handled within MappingConverter._apply_mirror.
# Additional standalone mirror function can be provided.

# ---- Part 6: Filtering & Selection ------------------------------------

class FilterEngine:
    """
    Filter a mapping by source or target names, regions, or categories.
    """
    @staticmethod
    def filter_by_sources(
        mapping: Dict[str, Any],
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Filter sources based on inclusion/exclusion lists or region/category.
        """
        if not mapping:
            return {}

        # Build set of allowed sources
        allowed = None
        if include is not None:
            allowed = set(include)
        elif region:
            allowed = set(FACIAL_REGIONS.get(region, []))
        elif category:
            allowed = set(EXPRESSION_CATEGORIES.get(category, []))

        # Exclude set
        excluded = set(exclude) if exclude else set()

        new_mapping = {}
        for source, value in mapping.items():
            if allowed is not None and source not in allowed:
                continue
            if source in excluded:
                continue
            new_mapping[source] = value

        return new_mapping

    @staticmethod
    def filter_by_targets(
        mapping: Dict[str, Any],
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Filter targets within each rule. This modifies the rules to keep only
        target names that match inclusion/exclusion.
        """
        if not mapping:
            return {}

        include_set = set(include) if include else None
        exclude_set = set(exclude) if exclude else set()

        new_mapping = {}
        for source, rules_data in mapping.items():
            if isinstance(rules_data, str):
                target = rules_data
                if include_set is not None and target not in include_set:
                    continue
                if target in exclude_set:
                    continue
                new_mapping[source] = target
            elif isinstance(rules_data, dict):
                target = rules_data.get("target", "")
                if include_set is not None and target not in include_set:
                    continue
                if target in exclude_set:
                    continue
                new_mapping[source] = rules_data
            elif isinstance(rules_data, list):
                new_rules = []
                for rule in rules_data:
                    if isinstance(rule, dict) and "target" in rule:
                        target = rule["target"]
                        if include_set is not None and target not in include_set:
                            continue
                        if target in exclude_set:
                            continue
                        new_rules.append(rule)
                    else:
                        # keep if not a dict or no target
                        new_rules.append(rule)
                if new_rules:
                    new_mapping[source] = new_rules
                # else omit source
            else:
                # keep as is
                new_mapping[source] = rules_data

        return new_mapping


# ---- Part 7: Merge & Split Operations ---------------------------------

class MergeSplitEngine:
    """
    Merge multiple mappings or split a mapping into parts.
    """
    @staticmethod
    def merge(
        mappings: List[Dict[str, Any]],
        operation: str = "sum",  # 'sum' or 'average'
        conflict: str = "add",   # 'add', 'replace', 'skip'
    ) -> Dict[str, Any]:
        """
        Merge multiple mappings into one.

        For each source, the rules are combined. If targets conflict,
        the operation determines how to combine multipliers etc.
        This is a simplified implementation: it merges simple mappings
        where each source maps to a target with a multiplier.
        For complex rules (with offsets, etc.), conflict resolution is more involved.
        """
        if not mappings:
            return {}

        if len(mappings) == 1:
            return copy.deepcopy(mappings[0])

        # For simplicity, we'll treat each mapping as a dict of source->target (or source->list of rules)
        # We'll use a target->list of (source, multiplier) accumulation.
        # We'll produce a mapping where each source maps to a list of targets.
        # A more robust approach would aggregate per target.

        # We'll accumulate per source a list of target rules.
        combined: Dict[str, Dict[str, float]] = {}  # source -> {target: total_multiplier}
        # We'll also store count for average.
        count_per_target: Dict[str, Dict[str, int]] = {}

        for map_idx, mp in enumerate(mappings):
            for source, rules_data in mp.items():
                if source not in combined:
                    combined[source] = {}
                    count_per_target[source] = {}
                # Get list of rule dicts
                if isinstance(rules_data, str):
                    rules = [{"target": rules_data, "multiplier": 1.0}]
                elif isinstance(rules_data, dict):
                    rules = [rules_data]
                elif isinstance(rules_data, list):
                    rules = rules_data
                else:
                    continue  # skip
                for rule in rules:
                    if not isinstance(rule, dict):
                        continue
                    target = rule.get("target")
                    if not target:
                        continue
                    multiplier = rule.get("multiplier", 1.0)
                    # If conflict is 'skip', and target already exists, skip this rule
                    if conflict == "skip" and target in combined[source]:
                        continue
                    if target not in combined[source]:
                        combined[source][target] = 0.0
                        count_per_target[source][target] = 0
                    if operation == "sum":
                        combined[source][target] += multiplier
                    elif operation == "average":
                        combined[source][target] += multiplier
                        count_per_target[source][target] += 1
                    elif operation == "replace":
                        combined[source][target] = multiplier  # last one wins
                    # if operation == "min" etc could be added.

        # Build final mapping
        result = {}
        for source, targets in combined.items():
            if operation == "average":
                # Divide by count
                for t in targets:
                    if count_per_target[source][t] > 0:
                        targets[t] /= count_per_target[source][t]
            # Build rules list
            rules_list = []
            for target, mult in targets.items():
                rules_list.append({"target": target, "multiplier": mult})
            result[source] = rules_list

        return result

    @staticmethod
    def split(
        mapping: Dict[str, Any],
        by: str,  # 'region', 'category', 'source_prefix', or custom function
        custom_filter: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Split a mapping into parts based on criteria.
        Returns dict of part_name -> sub-mapping.
        """
        parts: Dict[str, Dict[str, Any]] = {}

        if by == "region":
            for region, channels in FACIAL_REGIONS.items():
                filtered = FilterEngine.filter_by_sources(mapping, include=channels)
                if filtered:
                    parts[region] = filtered
        elif by == "category":
            for category, channels in EXPRESSION_CATEGORIES.items():
                filtered = FilterEngine.filter_by_sources(mapping, include=channels)
                if filtered:
                    parts[category] = filtered
        elif by == "source_prefix":
            # Group by prefix (e.g., 'mouth', 'eye', etc.)
            groups = {}
            for source in mapping.keys():
                # find first part before underscore or camel boundary
                # simple: split by underscore
                prefix = source.split('_')[0] if '_' in source else source
                groups.setdefault(prefix, []).append(source)
            for prefix, sources in groups.items():
                filtered = FilterEngine.filter_by_sources(mapping, include=sources)
                if filtered:
                    parts[prefix] = filtered
        elif by == "custom" and custom_filter is not None:
            # custom_filter should return a group key for each source
            groups = {}
            for source in mapping.keys():
                key = custom_filter(source)
                if key:
                    groups.setdefault(key, []).append(source)
            for key, sources in groups.items():
                filtered = FilterEngine.filter_by_sources(mapping, include=sources)
                if filtered:
                    parts[key] = filtered
        else:
            raise RemapOperationError(f"Unsupported split method: {by}")

        return parts


# ---- Part 8: Batch Remapping -----------------------------------------

class BatchRemapper:
    """
    Apply remap operations to a batch of mappings or presets.
    """
    def __init__(self, converter: MappingConverter):
        self._converter = converter

    def remap_batch(
        self,
        mappings: List[Dict[str, Any]],
        rename_sources: bool = True,
        rename_targets: bool = True,
        mirror: bool = False,
        mirror_rule: Optional[MirrorRule] = None,
        validate: bool = True,
    ) -> List[RemapResult]:
        """
        Remap a list of mappings.
        """
        results = []
        for mapping in mappings:
            result = self._converter.convert(
                mapping,
                rename_sources=rename_sources,
                rename_targets=rename_targets,
                mirror=mirror,
                mirror_rule=mirror_rule,
                validate=validate
            )
            results.append(result)
        return results


# ---- Part 9: Diagnostics ----------------------------------------------

class DiagnosticsCollector:
    """
    Collects diagnostic information during remap operations.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_ops = 0
        self.successes = 0
        self.failures = 0
        self.errors_list = []
        self.warnings_list = []
        self.renamed_sources_total = 0
        self.renamed_targets_total = 0
        self.mirrored_sources_total = 0
        self.mirrored_targets_total = 0

    def record_result(self, result: RemapResult):
        self.total_ops += 1
        if result.is_success:
            self.successes += 1
        else:
            self.failures += 1
        self.errors_list.extend(result.errors)
        self.warnings_list.extend(result.warnings)
        self.renamed_sources_total += len(result.renamed_sources)
        self.renamed_targets_total += len(result.renamed_targets)
        self.mirrored_sources_total += len(result.mirrored_sources)
        self.mirrored_targets_total += len(result.mirrored_targets)

    def get_report(self) -> Dict[str, Any]:
        return {
            "total_operations": self.total_ops,
            "successes": self.successes,
            "failures": self.failures,
            "total_errors": len(self.errors_list),
            "total_warnings": len(self.warnings_list),
            "renamed_sources": self.renamed_sources_total,
            "renamed_targets": self.renamed_targets_total,
            "mirrored_sources": self.mirrored_sources_total,
            "mirrored_targets": self.mirrored_targets_total,
        }


# ---- Part 10: Statistics ----------------------------------------------

class StatisticsEngine:
    """
    Computes statistics about a remap operation or collection.
    """
    @staticmethod
    def compute_statistics(result: RemapResult) -> RemapStatistics:
        stats = RemapStatistics()
        stats.total_sources_processed = len(result.mapping)  # approximate
        stats.renamed_sources = len(result.renamed_sources)
        stats.renamed_targets = len(result.renamed_targets)
        stats.mirrored_sources = len(result.mirrored_sources)
        stats.mirrored_targets = len(result.mirrored_targets)
        stats.errors = len(result.errors)
        stats.warnings = len(result.warnings)
        return stats

    @staticmethod
    def aggregate_stats(stats_list: List[RemapStatistics]) -> RemapStatistics:
        total = RemapStatistics()
        for s in stats_list:
            total.total_sources_processed += s.total_sources_processed
            total.total_targets_processed += s.total_targets_processed
            total.renamed_sources += s.renamed_sources
            total.renamed_targets += s.renamed_targets
            total.mirrored_sources += s.mirrored_sources
            total.mirrored_targets += s.mirrored_targets
            total.merged_mappings += s.merged_mappings
            total.split_parts += s.split_parts
            total.removed_sources += s.removed_sources
            total.removed_targets += s.removed_targets
            total.errors += s.errors
            total.warnings += s.warnings
            total.elapsed_ms += s.elapsed_ms
        return total


# ---- Part 11: Public API (ARKitRemapper) --------------------------------

class ARKitRemapper:
    """
    The main remapper class providing all remapping operations.

    Methods:
        remap: Rename sources/targets according to rules.
        mirror: Mirror a mapping (swap left/right).
        filter: Filter sources or targets.
        merge: Merge multiple mappings.
        split: Split a mapping into parts.
        batch_remap: Apply remap to a list of mappings.
        get_diagnostics: Return diagnostic summary.
        get_statistics: Return statistics of the last operation.
        reset_diagnostics: Reset internal diagnostics.
    """
    def __init__(self, rename_rules: Optional[List[RenameRule]] = None):
        """
        Args:
            rename_rules: Optional list of RenameRule objects to apply by default.
        """
        self._rename_rules = rename_rules or []
        self._converter = MappingConverter(self._rename_rules)
        self._diagnostics = DiagnosticsCollector()
        self._last_statistics: Optional[RemapStatistics] = None

    def remap(
        self,
        mapping: Dict[str, Any],
        rename_rules: Optional[List[RenameRule]] = None,
        rename_sources: bool = True,
        rename_targets: bool = True,
        mirror: bool = False,
        mirror_rule: Optional[MirrorRule] = None,
        validate: bool = True,
    ) -> RemapResult:
        """
        Remap a mapping using rename rules and optional mirroring.

        Args:
            mapping: The input mapping dict.
            rename_rules: Override the default rename rules.
            rename_sources: Whether to rename source channels.
            rename_targets: Whether to rename target channels.
            mirror: If True, mirror the mapping (swap left/right).
            mirror_rule: Custom mirror rule.
            validate: If True, validate the result mapping.

        Returns:
            RemapResult
        """
        # Use provided rules or default
        if rename_rules is not None:
            converter = MappingConverter(rename_rules)
        else:
            converter = self._converter

        result = converter.convert(
            mapping,
            rename_sources=rename_sources,
            rename_targets=rename_targets,
            mirror=mirror,
            mirror_rule=mirror_rule,
            validate=validate
        )

        self._diagnostics.record_result(result)
        self._last_statistics = StatisticsEngine.compute_statistics(result)

        return result

    def mirror(
        self,
        mapping: Dict[str, Any],
        mirror_rule: Optional[MirrorRule] = None,
        validate: bool = True,
    ) -> RemapResult:
        """
        Mirror a mapping (swap left/right). Equivalent to remap with mirror=True and no rename.
        """
        return self.remap(
            mapping,
            rename_rules=[],  # no renaming
            rename_sources=False,
            rename_targets=False,
            mirror=True,
            mirror_rule=mirror_rule,
            validate=validate
        )

    def filter_sources(
        self,
        mapping: Dict[str, Any],
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        region: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Filter mapping by source names, region, or category.
        """
        return FilterEngine.filter_by_sources(mapping, include, exclude, region, category)

    def filter_targets(
        self,
        mapping: Dict[str, Any],
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        Filter mapping by target names.
        """
        return FilterEngine.filter_by_targets(mapping, include, exclude)

    def merge(
        self,
        mappings: List[Dict[str, Any]],
        operation: str = "sum",
        conflict: str = "add",
    ) -> Dict[str, Any]:
        """
        Merge multiple mappings into one.

        Args:
            mappings: List of mapping dicts.
            operation: 'sum' or 'average' for combining multipliers.
            conflict: 'add', 'replace', or 'skip' for duplicate targets.

        Returns:
            Merged mapping dict.
        """
        return MergeSplitEngine.merge(mappings, operation, conflict)

    def split(
        self,
        mapping: Dict[str, Any],
        by: str = "region",
        custom_filter: Optional[Callable[[str], str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Split a mapping into parts by region, category, prefix, or custom.

        Args:
            mapping: The mapping to split.
            by: 'region', 'category', 'source_prefix', or 'custom'.
            custom_filter: Callable that returns a group key for each source.

        Returns:
            Dict of part_name -> sub-mapping.
        """
        return MergeSplitEngine.split(mapping, by, custom_filter)

    def batch_remap(
        self,
        mappings: List[Dict[str, Any]],
        rename_rules: Optional[List[RenameRule]] = None,
        rename_sources: bool = True,
        rename_targets: bool = True,
        mirror: bool = False,
        mirror_rule: Optional[MirrorRule] = None,
        validate: bool = True,
    ) -> List[RemapResult]:
        """
        Apply remap to a batch of mappings.
        """
        if rename_rules is not None:
            converter = MappingConverter(rename_rules)
        else:
            converter = self._converter
        batch = BatchRemapper(converter)
        results = batch.remap_batch(
            mappings,
            rename_sources=rename_sources,
            rename_targets=rename_targets,
            mirror=mirror,
            mirror_rule=mirror_rule,
            validate=validate
        )
        for res in results:
            self._diagnostics.record_result(res)
        # Aggregate statistics
        stats_list = [StatisticsEngine.compute_statistics(r) for r in results]
        self._last_statistics = StatisticsEngine.aggregate_stats(stats_list)
        return results

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic summary of all operations."""
        return self._diagnostics.get_report()

    def get_statistics(self) -> Optional[RemapStatistics]:
        """Return statistics of the last remap operation."""
        return self._last_statistics

    def reset_diagnostics(self):
        """Reset diagnostic collector."""
        self._diagnostics.reset()

    def clear_rules(self):
        """Clear the default rename rules."""
        self._rename_rules = []
        self._converter = MappingConverter([])


# ---- Public API --------------------------------------------------------

__all__ = [
    "ARKitRemapper",
    "RenameRule",
    "MirrorRule",
    "RemapResult",
    "RemapStatistics",
    "ARKitRemapperError",
    "RemapDefinitionError",
    "RemapOperationError",
]