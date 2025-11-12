"""Localization package for NRHOF.

This package provides localization services with modular translation files.

Structure:
    - service.py: Core localization service and logic
    - translations_en.py: English translations
    - translations_jp.py: Japanese translations
"""

from .service import (
    LANGUAGES,
    TRANSLATIONS,
    LocalizationService,
    add_language_change_listener,
    add_translation,
    get_all_translations,
    get_available_languages,
    get_language,
    get_language_name,
    get_localization_service,
    remove_language_change_listener,
    set_language,
    t,
    t_format,
    t_plural,
)

__all__ = [
    "LANGUAGES",
    "TRANSLATIONS",
    "LocalizationService",
    "set_language",
    "get_language",
    "t",
    "t_format",
    "t_plural",
    "get_all_translations",
    "add_language_change_listener",
    "remove_language_change_listener",
    "add_translation",
    "get_available_languages",
    "get_language_name",
    "get_localization_service",
]
