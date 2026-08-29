from __future__ import annotations

from limelight.demo import LOCATOR_LABEL_SCRIPT
from limelight.javascript import SCRIPTS, script
from limelight.overlay import SELECT_OPTION_LABELS_SCRIPT
from limelight.overlay.cursor import POINT_HIT_SCRIPT
from limelight.overlay.keyboard import INPUT_TYPE_SCRIPT


def test_every_script_on_disk_is_loaded() -> None:
    names_on_disk = sorted(path.name for path in SCRIPTS.iterdir() if path.name.endswith('.js'))

    assert names_on_disk == [
        'input_type.js',
        'locator_label.js',
        'point_hit.js',
        'select_option_labels.js',
    ]


def test_every_script_is_one_arrow_function() -> None:
    assert LOCATOR_LABEL_SCRIPT.startswith('element => {')
    assert INPUT_TYPE_SCRIPT.startswith('element => ')
    assert POINT_HIT_SCRIPT.startswith('(element, point) => {')
    assert SELECT_OPTION_LABELS_SCRIPT.startswith('element => ')


def test_script_reads_the_named_file() -> None:
    assert script('input_type.js') == INPUT_TYPE_SCRIPT
