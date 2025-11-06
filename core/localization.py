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
        'menu.option3': 'visualizers',
        'menu.option4': 'fate maker',
        
        # Footer
        'footer.settings': 'settings',
        'footer.company': 'BIG NERD INDUSTRIES INC. 2025',
        
        # Now Playing
        'now_playing.title': 'NOW PLAYING',
        
        # Common
        'common.back': 'back',
        'common.home': 'home',
        'common.esc': '<esc',
        'common.am': 'AM',
        'common.pm': 'PM',
        
        # Settings
        'settings.title': 'SETTINGS',
        'settings.language_english': 'English',
        'settings.language_japanese': 'Japanese',
        
        # Visualizers
        'visualizers.title': 'VISUALIZERS',
        
        # Splash
        'splash.title': 'NRHOF',
        'splash.loading': 'glow plugs starting...',
        
        # Intro
        'intro.line1': 'wake up, NRHOF...',
        'intro.line2': 'the matrix has you...',
        'intro.line3': 'follow the white rabbit...',
    },
    'jp': {
        # Menu
        'menu.title': 'NRHOF',
        'menu.option1': 'ナード・38',
        'menu.option2': 'ナード・18',
        'menu.option3': 'ビジュアライザ',
        'menu.option4': '運命師',
        
        # Footer
        'footer.settings': '設定',
        'footer.company': 'BIG NERD INDUSTRIES INC. 2025',
        
        # Now Playing
        'now_playing.title': 'Now Playing',
        
        # Common
        'common.back': '<戻る',
        'common.home': 'ホーム',
        'common.esc': '<戻る',
        'common.am': '午前',
        'common.pm': '午後',
        
        # Settings
        'settings.title': '設定',
        'settings.language_english': '英語',
        'settings.language_japanese': '日本語',
        
        # Visualizers
        'visualizers.title': 'ビジュアライザ',
        
        # Splash
        'splash.title': 'NRHOF',
        'splash.loading': '読み込み中...',
        
        # Intro
        'intro.line1': '覚えて起きた、NRHOF...',
        'intro.line2': 'マトリックスはあなたを捕らえていた...',
        'intro.line3': '白い豚を追っていこう...',
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