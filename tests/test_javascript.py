from __future__ import annotations

from limelight.capture.renderer import COLOR_SCHEME_DARK_SCRIPT
from limelight.components.modal import FORM_INVALID_SCRIPT
from limelight.components.navigator import SCROLL_INTO_VIEW_SCRIPT
from limelight.demo import LOCATOR_LABEL_SCRIPT
from limelight.javascript import SCRIPTS, script
from limelight.overlay.cursor import POINT_HIT_SCRIPT
from limelight.overlay.keyboard import INPUT_TYPE_SCRIPT
from limelight.overlay.overlay import SELECT_OPTION_LABELS_SCRIPT


def test_every_script_on_disk_is_loaded() -> None:
    names_on_disk = sorted(path.name for path in SCRIPTS.iterdir() if path.name.endswith('.js'))

    assert names_on_disk == [
        'color_scheme_dark.js',
        'form_invalid.js',
        'input_type.js',
        'locator_label.js',
        'point_hit.js',
        'scroll_into_view.js',
        'select_option_labels.js',
    ]


def test_every_script_is_one_arrow_function() -> None:
    assert LOCATOR_LABEL_SCRIPT.startswith('element => {')
    assert INPUT_TYPE_SCRIPT.startswith('element => ')
    assert POINT_HIT_SCRIPT.startswith('(element, point) => {')
    assert SELECT_OPTION_LABELS_SCRIPT.startswith('element => ')
    assert COLOR_SCHEME_DARK_SCRIPT.startswith('() => {')
    assert FORM_INVALID_SCRIPT.startswith('form => {')
    assert SCROLL_INTO_VIEW_SCRIPT.startswith('element => {')


def test_script_reads_the_named_file() -> None:
    assert script('input_type.js') == INPUT_TYPE_SCRIPT
