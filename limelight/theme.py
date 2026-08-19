from __future__ import annotations

from dataclasses import dataclass


COLOR_ACCENT_DEFAULT = '#4ea1ff'
COLOR_SPOTLIGHT_DEFAULT = '#ffd56b'
FONT_FAMILY_DEFAULT = "'Segoe UI', system-ui, -apple-system, sans-serif"


@dataclass(frozen=True)
class Theme:
    color_accent: str = COLOR_ACCENT_DEFAULT
    color_spotlight: str = COLOR_SPOTLIGHT_DEFAULT
    font_family: str = FONT_FAMILY_DEFAULT

    def __post_init__(self) -> None:
        if not self.color_accent.strip():
            message = 'color_accent must not be empty'
            raise ValueError(message)

        if not self.color_spotlight.strip():
            message = 'color_spotlight must not be empty'
            raise ValueError(message)

        if not self.font_family.strip():
            message = 'font_family must not be empty'
            raise ValueError(message)

    def payload(self) -> dict[str, str]:
        return {
            'colorAccent': self.color_accent,
            'colorSpotlight': self.color_spotlight,
            'fontFamily': self.font_family,
        }
