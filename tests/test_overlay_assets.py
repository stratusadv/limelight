from __future__ import annotations

from limelight.overlay.assets import ASSETS, OVERLAY_CSS, OVERLAY_JAVASCRIPT, SCRIPT_NAME


def script_names_on_disk() -> list[str]:
    return sorted(path.name for path in ASSETS.iterdir() if path.name.endswith('.js'))


def test_the_bundle_is_the_only_script_on_disk() -> None:
    assert script_names_on_disk() == [SCRIPT_NAME]


def test_bundle_is_one_callable_expression() -> None:
    lines = OVERLAY_JAVASCRIPT.splitlines()

    assert lines[0] == '(config) => {'
    assert lines[-2] == 'return limelight.install(config);'
    assert lines[-1] == '}'


def test_stylesheet_needs_no_interpolation() -> None:
    assert '${' not in OVERLAY_CSS
    assert '`' not in OVERLAY_CSS
