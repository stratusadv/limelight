from __future__ import annotations

from importlib.resources import files


ASSETS = files('limelight.overlay').joinpath('assets')

STYLESHEET_NAME = 'overlay.css'

PART_NAMES = (
    'dom.js',
    'animation.js',
    'cursor.js',
    'keys.js',
    'spot.js',
    'control.js',
    'api.js',
    'install.js',
)


def _read(name: str) -> str:
    """
    A function that reads a bundled overlay asset by file name.

    :param name: The file name of the asset under limelight/overlay/assets.
    :return: The contents of the asset.
    """

    return ASSETS.joinpath(name).read_text(encoding='utf-8')


def _javascript_compose() -> str:
    """
    A function that joins the overlay scripts into one installer expression.

    The parts are concatenated into a single arrow function rather than loaded as
    modules, because the overlay is injected through an evaluate call that takes
    one expression and has no module loader behind it.

    :return: The source of the installer, which returns the overlay API.
    """

    parts = '\n'.join(_read(name) for name in PART_NAMES)

    return f'(config) => {{\n{parts}\nreturn install();\n}}'


OVERLAY_CSS = _read(STYLESHEET_NAME)
OVERLAY_JAVASCRIPT = _javascript_compose()
