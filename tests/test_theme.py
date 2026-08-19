from __future__ import annotations

import pytest

from limelight.theme import COLOR_ACCENT_DEFAULT, Theme


def test_payload_uses_javascript_keys() -> None:
    theme = Theme()

    assert theme.payload() == {
        'colorAccent': COLOR_ACCENT_DEFAULT,
        'colorSpotlight': theme.color_spotlight,
        'fontFamily': theme.font_family,
    }


def test_custom_colors_flow_through() -> None:
    theme = Theme(color_accent='#ff0000')

    assert theme.payload()['colorAccent'] == '#ff0000'


def test_empty_color_rejected() -> None:
    with pytest.raises(ValueError, match='color_accent'):
        Theme(color_accent='   ')


def test_empty_font_rejected() -> None:
    with pytest.raises(ValueError, match='font_family'):
        Theme(font_family='')
