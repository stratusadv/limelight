from __future__ import annotations

from importlib.resources import files


ASSETS = files('limelight.overlay').joinpath('assets')

SCRIPT_NAME = 'overlay.js'
STYLESHEET_NAME = 'overlay.css'


def _read(name: str) -> str:
    """
    A function that reads a bundled overlay asset by file name.

    :param name: The file name of the asset under limelight/overlay/assets.
    :return: The contents of the asset.
    """

    return ASSETS.joinpath(name).read_text(encoding='utf-8')


OVERLAY_CSS = _read(STYLESHEET_NAME)
OVERLAY_JAVASCRIPT = _read(SCRIPT_NAME)
