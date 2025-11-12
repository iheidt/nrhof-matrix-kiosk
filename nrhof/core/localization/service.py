"""Core localization service with event-driven language switching.

This module provides the core localization functionality including:
- Language management and switching
- Translation lookup with fallbacks
- Variable substitution and pluralization
- Language change listeners
- Service class with caching
"""

from collections.abc import Callable

from .translations_en import TRANSLATIONS_EN
from .translations_jp import TRANSLATIONS_JP

# Supported languages
LANGUAGES = ["en", "jp"]

# Combined translation dictionary
TRANSLATIONS = {
    "en": TRANSLATIONS_EN,
    "jp": TRANSLATIONS_JP,
}

# Current language (default to English)
_current_language = "en"

# Language change listeners
_language_change_listeners: list[Callable[[str, str], None]] = []


def set_language(lang: str, event_bus=None):
    """Set the current language and notify listeners.

    Args:
        lang: Language code ('en', 'jp', etc.)
        event_bus: Optional event bus instance (defaults to global)
    """
    global _current_language
    old_lang = _current_language

    if lang in LANGUAGES:
        _current_language = lang
    else:
        print(f"Warning: Language '{lang}' not supported, using 'en'")
        _current_language = "en"

    # Notify listeners if language changed
    if old_lang != _current_language:
        _notify_language_change(old_lang, _current_language)

        # Emit event bus event if available
        try:
            from nrhof.core.event_bus import EventType, get_event_bus

            bus = event_bus or get_event_bus()
            bus.emit(
                EventType.LANGUAGE_CHANGED,
                {"old_language": old_lang, "new_language": _current_language},
                source="localization",
            )
        except (ImportError, AttributeError):
            pass

        # Log language change
        print(f"[LOCALIZATION] Language changed: {old_lang} -> {_current_language}")


def get_language() -> str:
    """Get the current language code."""
    return _current_language


def t(key: str, default: str = None) -> str:
    """Translate a key to the current language.

    Args:
        key: Translation key (e.g., 'menu.title')
        default: Default text if key not found

    Returns:
        Translated string
    """
    lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS["en"])
    return lang_dict.get(key, default or key)


def get_all_translations(key: str) -> dict:
    """Get all language translations for a key.

    Args:
        key: Translation key

    Returns:
        Dict mapping language codes to translations
    """
    return {lang: TRANSLATIONS[lang].get(key, key) for lang in LANGUAGES}


def add_language_change_listener(callback: Callable[[str, str], None]):
    """Register a callback for language changes.

    Args:
        callback: Function(old_lang, new_lang) to call when language changes
    """
    if callback not in _language_change_listeners:
        _language_change_listeners.append(callback)


def remove_language_change_listener(callback: Callable[[str, str], None]):
    """Unregister a language change callback.

    Args:
        callback: Previously registered callback
    """
    if callback in _language_change_listeners:
        _language_change_listeners.remove(callback)


def _notify_language_change(old_lang: str, new_lang: str):
    """Notify all listeners of language change.

    Args:
        old_lang: Previous language code
        new_lang: New language code
    """
    for listener in _language_change_listeners:
        try:
            listener(old_lang, new_lang)
        except Exception as e:
            print(f"Error in language change listener: {e}")


def t_format(key: str, **kwargs) -> str:
    """Translate a key with variable substitution.

    Args:
        key: Translation key
        **kwargs: Variables to substitute (e.g., {name}, {count})

    Returns:
        Formatted translated string

    Example:
        t_format('greeting.hello', name='Alice') -> 'Hello, Alice!'
    """
    template = t(key)
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError) as e:
        print(f"Warning: Failed to format translation '{key}': {e}")
        return template


def t_plural(key: str, count: int, **kwargs) -> str:
    """Translate with pluralization support.

    Args:
        key: Translation key (will try key_plural for count != 1)
        count: Count for pluralization
        **kwargs: Additional format variables

    Returns:
        Translated and formatted string

    Example:
        t_plural('items.count', 1) -> '1 item'
        t_plural('items.count', 5) -> '5 items'
    """
    # Try plural form first if count != 1
    if count != 1:
        plural_key = f"{key}_plural"
        lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS["en"])
        if plural_key in lang_dict:
            template = lang_dict[plural_key]
            return template.format(count=count, **kwargs)

    # Fall back to singular form
    return t_format(key, count=count, **kwargs)


def add_translation(lang: str, key: str, value: str):
    """Add or update a translation at runtime.

    Args:
        lang: Language code
        key: Translation key
        value: Translation value
    """
    if lang not in TRANSLATIONS:
        TRANSLATIONS[lang] = {}
    TRANSLATIONS[lang][key] = value


def get_available_languages() -> list[str]:
    """Get list of available language codes.

    Returns:
        List of language codes
    """
    return LANGUAGES.copy()


def get_language_name(lang: str) -> str:
    """Get the display name for a language.

    Args:
        lang: Language code

    Returns:
        Display name
    """
    names = {"en": "English", "jp": "日本語"}
    return names.get(lang, lang)


class LocalizationService:
    """Service class for managing localization with lifecycle integration.

    Note:
        This service wraps the functional API (t(), t_format(), etc.) and adds
        caching, listener management, and lifecycle integration. For simple
        translations, the functional API (t()) is preferred for performance.
    """

    def __init__(self):
        """Initialize localization service."""
        self._listeners: list[Callable[[str, str], None]] = []
        self._cache: dict[str, str] = {}
        self._cache_enabled = True

    def set_language(self, lang: str):
        """Set language through service."""
        set_language(lang)
        if self._cache_enabled:
            self._cache.clear()

    def get_language(self) -> str:
        """Get current language."""
        return get_language()

    def translate(self, key: str, default: str = None, **kwargs) -> str:
        """Translate with optional formatting.

        This method wraps the t() function and adds caching. For simple use cases,
        calling t() directly is more efficient.

        Args:
            key: Translation key
            default: Default value if key not found
            **kwargs: Format variables

        Returns:
            Translated string
        """
        if kwargs:
            # Use t_format for variable substitution
            return t_format(key, **kwargs)

        # Use cache if enabled
        if self._cache_enabled:
            cache_key = f"{_current_language}:{key}"
            if cache_key in self._cache:
                return self._cache[cache_key]
            # Delegate to t() function for actual translation
            result = t(key, default)
            self._cache[cache_key] = result
            return result

        # Direct delegation to t() when cache disabled
        return t(key, default)

    def add_listener(self, callback: Callable[[str, str], None]):
        """Add language change listener."""
        add_language_change_listener(callback)
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str, str], None]):
        """Remove language change listener."""
        remove_language_change_listener(callback)
        if callback in self._listeners:
            self._listeners.remove(callback)

    def clear_cache(self):
        """Clear translation cache."""
        self._cache.clear()

    def enable_cache(self, enabled: bool = True):
        """Enable or disable translation caching."""
        self._cache_enabled = enabled
        if not enabled:
            self._cache.clear()


# Global service instance
_localization_service: LocalizationService | None = None


def get_localization_service() -> LocalizationService:
    """Get the global localization service instance.

    Returns:
        LocalizationService instance
    """
    global _localization_service
    if _localization_service is None:
        _localization_service = LocalizationService()
    return _localization_service
