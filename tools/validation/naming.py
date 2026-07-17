# -*- coding: utf-8 -*-
"""
validation/naming.py

Naming convention validation for controllers, joints, and meshes.
"""

import re
from typing import List, Optional, Dict, Tuple, Pattern
from .validator import ValidationResult


class NamingValidator:
    """
    Validate objects against naming conventions.

    Supports:
        - Prefix/suffix rules
        - Case rules (camelCase, snake_case, PascalCase)
        - Length constraints
        - Reserved words
        - Character set constraints
    """

    def __init__(self):
        self._rules: Dict[str, any] = {}
        self._errors: List[str] = []

    # =========================================================================
    # RULE DEFINITION
    # =========================================================================

    def set_rule(self, rule_type: str, value: any) -> None:
        """
        Set a naming rule.

        Rule types:
            - 'prefix': required prefix (e.g., "CTRL_")
            - 'suffix': required suffix (e.g., "_CTRL")
            - 'case': one of 'camel', 'snake', 'pascal', 'upper', 'lower'
            - 'min_length': minimum length
            - 'max_length': maximum length
            - 'allowed_chars': regex for allowed characters
            - 'forbidden_chars': regex for forbidden characters
            - 'reserved_words': list of words to avoid
        """
        self._rules[rule_type] = value

    def set_rules(self, rules: Dict[str, any]) -> None:
        """Set multiple rules at once."""
        self._rules.update(rules)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate(self, name: str) -> ValidationResult:
        """
        Validate a single name against the active naming rules.

        Returns:
            ValidationResult with issues.
        """
        result = ValidationResult()

        if not name:
            result.add_error("Name is empty.")
            return result

        # Check rules
        for rule_type, rule_value in self._rules.items():
            if rule_type == 'prefix':
                if not name.startswith(rule_value):
                    result.add_error(f"Name '{name}' must start with '{rule_value}'.")

            elif rule_type == 'suffix':
                if not name.endswith(rule_value):
                    result.add_error(f"Name '{name}' must end with '{rule_value}'.")

            elif rule_type == 'case':
                if rule_value == 'camel':
                    if not (name[0].islower() and any(c.isupper() for c in name[1:])):
                        result.add_error(f"Name '{name}' must be camelCase.")
                elif rule_value == 'snake':
                    if not all(c.islower() or c == '_' for c in name):
                        result.add_error(f"Name '{name}' must be snake_case (lowercase with underscores).")
                elif rule_value == 'pascal':
                    if not (name[0].isupper() and not any(c.islower() for c in name[1:])):
                        result.add_error(f"Name '{name}' must be PascalCase.")
                elif rule_value == 'upper':
                    if not name.isupper():
                        result.add_error(f"Name '{name}' must be uppercase.")
                elif rule_value == 'lower':
                    if not name.islower():
                        result.add_error(f"Name '{name}' must be lowercase.")

            elif rule_type == 'min_length':
                if len(name) < rule_value:
                    result.add_error(f"Name '{name}' is too short (minimum {rule_value} characters).")

            elif rule_type == 'max_length':
                if len(name) > rule_value:
                    result.add_error(f"Name '{name}' is too long (maximum {rule_value} characters).")

            elif rule_type == 'allowed_chars':
                pattern = re.compile(rule_value)
                if not pattern.match(name):
                    result.add_error(f"Name '{name}' contains disallowed characters (allowed: {rule_value}).")

            elif rule_type == 'forbidden_chars':
                pattern = re.compile(rule_value)
                if pattern.search(name):
                    result.add_error(f"Name '{name}' contains forbidden characters ({rule_value}).")

            elif rule_type == 'reserved_words':
                if name in rule_value:
                    result.add_error(f"Name '{name}' is a reserved word.")

        return result

    def validate_list(self, names: List[str]) -> ValidationResult:
        """Validate a list of names against the naming rules."""
        combined = ValidationResult()
        for n in names:
            r = self.validate(n)
            combined.merge(r)
        return combined

    # =========================================================================
    # NAMING CONVENTIONS
    # =========================================================================

    def validate_controller(self, name: str) -> ValidationResult:
        """Validate a controller name using typical FaceIT conventions."""
        # Use controller-specific rules
        self.set_rules({
            'suffix': '_CTRL',
            'case': 'pascal',
            'min_length': 4,
            'max_length': 30,
            'allowed_chars': r'^[A-Za-z0-9_]+$',
            'reserved_words': ['CTRL', 'JOINT', 'MESH'],
        })
        return self.validate(name)

    def validate_joint(self, name: str) -> ValidationResult:
        """Validate a joint name using typical conventions."""
        self.set_rules({
            'suffix': '_JNT',
            'case': 'snake',
            'min_length': 3,
            'allowed_chars': r'^[a-z0-9_]+$',
            'reserved_words': ['joint', 'bone', 'skeleton'],
        })
        return self.validate(name)

    def validate_mesh(self, name: str) -> ValidationResult:
        """Validate a mesh name."""
        self.set_rules({
            'suffix': '_GEO',
            'case': 'lower',
            'min_length': 3,
        })
        return self.validate(name)

    # =========================================================================
    # SUGGESTIONS
    # =========================================================================

    def suggest_correction(self, name: str) -> Optional[str]:
        """
        Suggest a corrected name based on active rules.

        Returns:
            Suggested name, or None if no change needed.
        """
        result = self.validate(name)
        if result.valid:
            return None

        corrected = name
        # Apply simple corrections
        if 'prefix' in self._rules and not name.startswith(self._rules['prefix']):
            corrected = self._rules['prefix'] + name
        if 'suffix' in self._rules and not name.endswith(self._rules['suffix']):
            corrected = corrected + self._rules['suffix']
        # Case correction
        if 'case' in self._rules:
            if self._rules['case'] == 'snake':
                # Convert to snake_case (simplified)
                corrected = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', corrected).lower()
            elif self._rules['case'] == 'pascal':
                corrected = ''.join(word.capitalize() for word in re.split(r'[_\s]+', corrected))
            elif self._rules['case'] == 'upper':
                corrected = corrected.upper()
            elif self._rules['case'] == 'lower':
                corrected = corrected.lower()

        # Check if corrected still matches rules
        corrected_result = self.validate(corrected)
        if corrected_result.valid:
            return corrected
        return None