from __future__ import annotations

from limelight.overlay.assets import ASSETS, OVERLAY_CSS, OVERLAY_JAVASCRIPT, PART_NAMES


def part_names_on_disk() -> list[str]:
    return sorted(path.name for path in ASSETS.iterdir() if path.name.endswith('.js'))


def test_every_part_on_disk_is_composed() -> None:
    assert part_names_on_disk() == sorted(PART_NAMES)


def test_install_is_the_last_part() -> None:
    assert PART_NAMES[-1] == 'install.js'


def test_bundle_is_one_callable_expression() -> None:
    lines = OVERLAY_JAVASCRIPT.split('\n')

    assert lines[0] == '(config) => {'
    assert lines[-2] == 'return install();'
    assert lines[-1] == '}'


def test_bundle_carries_every_part() -> None:
    for name in PART_NAMES:
        body = ASSETS.joinpath(name).read_text(encoding='utf-8')

        assert body.strip() in OVERLAY_JAVASCRIPT


def test_stylesheet_needs_no_interpolation() -> None:
    assert '${' not in OVERLAY_CSS
    assert '`' not in OVERLAY_CSS


def test_theme_properties_are_set_by_the_installer() -> None:
    installer = ASSETS.joinpath('install.js').read_text(encoding='utf-8')

    assert "setProperty('--limelight-accent'" in installer
    assert "setProperty('--limelight-spotlight'" in installer
    assert "setProperty('--limelight-font'" in installer
