from __future__ import annotations

from dataclasses import dataclass


COLOR_ACCENT_DEFAULT = '#4ea1ff'
COLOR_SPOTLIGHT_DEFAULT = '#ffd56b'
FONT_FAMILY_DEFAULT = "'Segoe UI', system-ui, -apple-system, sans-serif"


@dataclass(frozen=True)
class Theme:
    """
    A palette for the overlay drawn on top of the recorded page.

    This class holds the colors and the font used by the cursor, the spotlight,
    and the caption bar.
    """

    color_accent: str = COLOR_ACCENT_DEFAULT
    color_spotlight: str = COLOR_SPOTLIGHT_DEFAULT
    font_family: str = FONT_FAMILY_DEFAULT

    def __post_init__(self) -> None:
        """
        A method that rejects a theme with an empty field.

        :raises ValueError: If any of the colors or the font family is blank.
        """

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
        """
        A method that renders the theme as the object handed to the overlay.

        :return: The theme fields keyed by their JavaScript names.
        """

        return {
            'colorAccent': self.color_accent,
            'colorSpotlight': self.color_spotlight,
            'fontFamily': self.font_family,
        }
