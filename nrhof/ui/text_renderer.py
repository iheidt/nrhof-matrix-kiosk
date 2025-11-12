#!/usr/bin/env python3
"""Text rendering strategies for different languages and font requirements."""

import re
from abc import ABC, abstractmethod

import pygame


def contains_japanese(text: str) -> bool:
    """Check if text contains Japanese characters (Hiragana, Katakana, or Kanji).

    Args:
        text: Text to check

    Returns:
        True if text contains any Japanese characters
    """
    for char in text:
        code = ord(char)
        # Hiragana: U+3040 to U+309F
        # Katakana: U+30A0 to U+30FF
        # Kanji (CJK Unified Ideographs): U+4E00 to U+9FFF
        # CJK Compatibility Ideographs: U+F900 to U+FAFF
        if (
            0x3040 <= code <= 0x309F  # Hiragana
            or 0x30A0 <= code <= 0x30FF  # Katakana
            or 0x4E00 <= code <= 0x9FFF  # Kanji
            or 0xF900 <= code <= 0xFAFF
        ):  # CJK Compatibility
            return True
    return False


def is_japanese_char(char: str) -> bool:
    """Check if a single character is Japanese.

    Args:
        char: Single character to check

    Returns:
        True if character is Japanese (Hiragana, Katakana, or Kanji)
    """
    if not char:
        return False
    code = ord(char)
    return (
        0x3040 <= code <= 0x309F  # Hiragana
        or 0x30A0 <= code <= 0x30FF  # Katakana
        or 0x4E00 <= code <= 0x9FFF  # Kanji
        or 0xF900 <= code <= 0xFAFF
    )  # CJK Compatibility


class TextRenderer(ABC):
    """Abstract base class for text rendering strategies."""

    @abstractmethod
    def render(
        self,
        text: str,
        size: int,
        font_type: str,
        color: tuple[int, int, int],
        antialias: bool = True,
    ) -> pygame.Surface:
        """Render text to a pygame surface.

        Args:
            text: Text to render
            size: Font size in points
            font_type: 'primary', 'secondary', or 'label'
            color: RGB color tuple
            antialias: Whether to use antialiasing

        Returns:
            pygame.Surface with rendered text
        """
        pass


class SimpleTextRenderer(TextRenderer):
    """Simple text renderer using a single font for entire text."""

    def __init__(self, font_loader):
        """Initialize with a font loader function.

        Args:
            font_loader: Function that takes (size, font_type, text) and returns pygame.Font
        """
        self.font_loader = font_loader

    def render(
        self,
        text: str,
        size: int,
        font_type: str,
        color: tuple[int, int, int],
        antialias: bool = True,
    ) -> pygame.Surface:
        """Render text with a single font."""
        font = self.font_loader(size, font_type, text)
        return font.render(text, antialias, color)


class MixedFontTextRenderer(TextRenderer):
    """Text renderer that uses different fonts for numbers vs other characters.

    This is useful for Japanese text where numbers should use English fonts
    while Japanese characters use Japanese fonts.
    """

    def __init__(self, localized_font_loader, english_font_loader):
        """Initialize with font loaders.

        Args:
            localized_font_loader: Function for localized fonts (size, font_type, text) -> Font
            english_font_loader: Function for English fonts (size, font_type) -> Font
        """
        self.localized_font_loader = localized_font_loader
        self.english_font_loader = english_font_loader

    def render(
        self,
        text: str,
        size: int,
        font_type: str,
        color: tuple[int, int, int],
        antialias: bool = True,
    ) -> pygame.Surface:
        """Render text with mixed fonts: numbers use English, others use localized."""
        # Check if text contains numbers
        if not any(c.isdigit() for c in text):
            # No numbers, use simple rendering
            font = self.localized_font_loader(size, font_type, text)
            return font.render(text, antialias, color)

        # Split text into segments: numbers vs non-numbers
        segments = re.findall(r"\d+|\D+", text)

        # Render each segment
        surfaces = []
        for segment in segments:
            if any(c.isdigit() for c in segment):
                # Numbers use English font
                font = self.english_font_loader(size, font_type)
            else:
                # Other characters use localized font
                font = self.localized_font_loader(size, font_type, segment)

            surface = font.render(segment, antialias, color)
            surfaces.append(surface)

        # If only one segment, return it directly
        if len(surfaces) == 1:
            return surfaces[0]

        # Combine surfaces horizontally
        return self._combine_surfaces(surfaces)

    def _combine_surfaces(self, surfaces: list) -> pygame.Surface:
        """Combine multiple surfaces horizontally with baseline alignment.

        Args:
            surfaces: List of pygame.Surface objects to combine

        Returns:
            Combined pygame.Surface
        """
        total_width = sum(s.get_width() for s in surfaces)
        max_height = max(s.get_height() for s in surfaces)

        combined = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        combined.fill((0, 0, 0, 0))  # Transparent background

        x_offset = 0
        for surface in surfaces:
            # Vertically align to baseline (bottom of surface)
            y_offset = max_height - surface.get_height()
            combined.blit(surface, (x_offset, y_offset))
            x_offset += surface.get_width()

        return combined


class CharacterMixedFontTextRenderer(TextRenderer):
    """Text renderer that detects Japanese characters and uses appropriate fonts per character.

    This renderer checks each character and uses Japanese fonts (Noto Sans JP) for Japanese
    characters while keeping English fonts for ASCII/Latin characters. This allows mixed
    English/Japanese text like "ura • 椎名林檎" to render correctly.
    """

    def __init__(self, english_font_loader, japanese_font_loader):
        """Initialize with font loaders.

        Args:
            english_font_loader: Function for English fonts (size, font_type) -> Font
            japanese_font_loader: Function for Japanese fonts (size, font_type, text) -> Font
        """
        self.english_font_loader = english_font_loader
        self.japanese_font_loader = japanese_font_loader

    def render(
        self,
        text: str,
        size: int,
        font_type: str,
        color: tuple[int, int, int],
        antialias: bool = True,
    ) -> pygame.Surface:
        """Render text with per-character font selection based on character type."""
        # Quick check: if no Japanese characters, use English font for everything
        if not contains_japanese(text):
            font = self.english_font_loader(size, font_type)
            return font.render(text, antialias, color)

        # Split into segments of consecutive same-type characters
        segments = []
        current_segment = ""
        current_is_japanese = None

        for char in text:
            char_is_japanese = is_japanese_char(char)

            if current_is_japanese is None:
                # First character
                current_segment = char
                current_is_japanese = char_is_japanese
            elif char_is_japanese == current_is_japanese:
                # Same type, add to current segment
                current_segment += char
            else:
                # Type changed, save current segment and start new one
                segments.append((current_segment, current_is_japanese))
                current_segment = char
                current_is_japanese = char_is_japanese

        # Add final segment
        if current_segment:
            segments.append((current_segment, current_is_japanese))

        # Render each segment with appropriate font
        surfaces = []
        for segment_text, is_japanese in segments:
            if is_japanese:
                # Use Japanese font (Noto Sans JP)
                font = self.japanese_font_loader(size, font_type, segment_text)
            else:
                # Use English font (IBM Plex Mono, etc.)
                font = self.english_font_loader(size, font_type)

            surface = font.render(segment_text, antialias, color)
            surfaces.append(surface)

        # If only one segment, return it directly
        if len(surfaces) == 1:
            return surfaces[0]

        # Combine surfaces horizontally
        return self._combine_surfaces(surfaces)

    def _combine_surfaces(self, surfaces: list) -> pygame.Surface:
        """Combine multiple surfaces horizontally with baseline alignment.

        Args:
            surfaces: List of pygame.Surface objects to combine

        Returns:
            Combined pygame.Surface
        """
        total_width = sum(s.get_width() for s in surfaces)
        max_height = max(s.get_height() for s in surfaces)

        combined = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        combined.fill((0, 0, 0, 0))  # Transparent background

        x_offset = 0
        for surface in surfaces:
            # Vertically align to baseline (bottom of surface)
            y_offset = max_height - surface.get_height()
            combined.blit(surface, (x_offset, y_offset))
            x_offset += surface.get_width()

        return combined


class TextRendererFactory:
    """Factory for creating appropriate text renderer based on language and requirements."""

    @staticmethod
    def create_renderer(language: str, localized_font_loader, english_font_loader) -> TextRenderer:
        """Create appropriate text renderer for the given language.

        Args:
            language: Language code (e.g., 'en', 'jp')
            localized_font_loader: Function for localized fonts
            english_font_loader: Function for English fonts

        Returns:
            TextRenderer instance
        """
        if language == "jp":
            # Japanese needs mixed font rendering for numbers
            return MixedFontTextRenderer(localized_font_loader, english_font_loader)
        else:
            # Other languages use simple rendering
            return SimpleTextRenderer(localized_font_loader)
