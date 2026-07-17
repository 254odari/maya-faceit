"""
maya_faceit/services/localization/localization.py

Multi‑language support for UI strings.
"""

import logging
import json
import os
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class LocalizationService:
    """
    Manages translations for the UI and messages.
    Uses JSON translation files.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._language = "en"
        self._translations: Dict[str, Dict[str, str]] = {}
        self._loaded_languages: set = set()
        self._locale_dir: Optional[str] = None
        logger.debug("LocalizationService initialized (default: en)")

    def set_locale_dir(self, path: str) -> None:
        """Set the directory where translation JSON files are stored."""
        self._locale_dir = path
        os.makedirs(path, exist_ok=True)

    def load_language(self, language_code: str) -> bool:
        """Load translations for a specific language."""
        if language_code in self._loaded_languages:
            return True
        if not self._locale_dir:
            logger.warning("Locale directory not set.")
            return False
        filepath = os.path.join(self._locale_dir, f"{language_code}.json")
        if not os.path.exists(filepath):
            logger.warning(f"Translation file for '{language_code}' not found.")
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self._translations[language_code] = json.load(f)
            self._loaded_languages.add(language_code)
            logger.info(f"Loaded language: {language_code}")
            return True
        except Exception as e:
            logger.error(f"Failed to load language '{language_code}': {e}")
            return False

    def set_language(self, language_code: str) -> None:
        """Switch the current language."""
        if language_code not in self._loaded_languages:
            if not self.load_language(language_code):
                return
        self._language = language_code
        logger.info(f"Switched to language: {language_code}")

    def get_language(self) -> str:
        return self._language

    def tr(self, key: str, default: Optional[str] = None) -> str:
        """
        Translate a string key into the current language.
        If not found, returns the default (or the key itself).
        """
        if self._language in self._translations:
            translation = self._translations[self._language].get(key)
            if translation is not None:
                return translation
        return default if default is not None else key

    def get_available_languages(self) -> list:
        """Return a list of available language codes."""
        if not self._locale_dir or not os.path.exists(self._locale_dir):
            return ["en"]
        return [f.replace(".json", "") for f in os.listdir(self._locale_dir) if f.endswith(".json")]

    def create_translation_template(self, keys: list) -> None:
        """Create a skeleton translation file for a new language (English)."""
        if not self._locale_dir:
            logger.warning("Locale directory not set.")
            return
        template_path = os.path.join(self._locale_dir, "en.json")
        if os.path.exists(template_path):
            logger.info("English template already exists.")
            return
        # Build a dict with keys as both key and value (placeholder)
        template = {key: key for key in keys}
        try:
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            logger.info(f"Created translation template at {template_path}")
        except Exception as e:
            logger.error(f"Failed to create template: {e}")