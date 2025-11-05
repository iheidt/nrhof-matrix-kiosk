"""Localization module for multi-language support."""

# Supported languages
LANGUAGES = ['en', 'jp']

# Translation dictionary
TRANSLATIONS = {
    'en': {
        # Menu
        'menu.title': 'NRHOF',
        'menu.option1': 'NR-38',
        'menu.option2': 'NR-18',
        'menu.option3': 'visualizer',
        'menu.option4': 'fate maker',
        
        # Footer
        'footer.settings': 'settings',
        'footer.company': 'BIG NERD INDUSTRIES INC. 2025',
        
        # Now Playing
        'now_playing.title': 'NOW PLAYING',
        
        # Experience 1 Hub
        'exp1.title': 'VISUALIZER',
        'exp1.spectrum': 'spectrum bars',
        'exp1.waveform': 'waveform',
        'exp1.lissajous': 'lissajous',
        
        # Experience 2 Hub
        'exp2.title': 'NR-38',
        'exp2.videos': 'music videos',
        
        # Common
        'common.back': 'back',
        'common.home': 'home',
        
        # Splash
        'splash.title': 'NRHOF',
        'splash.loading': 'loading...',
        
        # Intro
        'intro.line1': 'wake up, NRHOF...',
        'intro.line2': 'the matrix has you...',
        'intro.line3': 'follow the white rabbit...',
    },
    'jp': {
        # Menu
        'menu.title': 'NRHOF',
        'menu.option1': 'NR-38',
        'menu.option2': 'NR-18',
        'menu.option3': 'visualizador',
        'menu.option4': 'creador de destino',
        
        # Footer
        'footer.settings': 'configuración',
        'footer.company': 'BIG NERD INDUSTRIES INC. 2025',
        
        # Now Playing
        'now_playing.title': 'REPRODUCIENDO',
        
        # Experience 1 Hub
        'exp1.title': 'VISUALIZADOR',
        'exp1.spectrum': 'barras de espectro',
        'exp1.waveform': 'forma de onda',
        'exp1.lissajous': 'lissajous',
        
        # Experience 2 Hub
        'exp2.title': 'NR-38',
        'exp2.videos': 'videos musicales',
        
        # Common
        'common.back': 'atrás',
        'common.home': 'inicio',
        
        # Splash
        'splash.title': 'NRHOF',
        'splash.loading': '???',
        
        # Intro
        'intro.line1': '???...',
        'intro.line2': '???...',
        'intro.line3': '???...',
    }
}

# Current language (default to English)
_current_language = 'en'


def set_language(lang: str):
    """Set the current language.
    
    Args:
        lang: Language code ('en', 'jp', etc.)
    """
    global _current_language
    if lang in LANGUAGES:
        _current_language = lang
    else:
        print(f"Warning: Language '{lang}' not supported, using 'en'")
        _current_language = 'en'


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
    lang_dict = TRANSLATIONS.get(_current_language, TRANSLATIONS['en'])
    return lang_dict.get(key, default or key)


def get_all_translations(key: str) -> dict:
    """Get all language translations for a key.
    
    Args:
        key: Translation key
    
    Returns:
        Dict mapping language codes to translations
    """
    return {lang: TRANSLATIONS[lang].get(key, key) for lang in LANGUAGES}