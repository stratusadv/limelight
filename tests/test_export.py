from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

from limelight.export import Export, TextExport, exports_run
from limelight.export.chapters import chapters_export
from limelight.export.subtitles import subtitles_export
from limelight.export.walkthrough import walkthrough_export

from events import events_sample

if TYPE_CHECKING:
    from pathlib import Path


def test_text_export_writes_the_rendered_file(tmp_path: Path) -> None:
    export = TextExport('notes.txt', lambda events: f'{len(events)} events\n')

    path = export.export(events_sample(), tmp_path)

    assert path == tmp_path / 'notes.txt'
    assert path.read_text(encoding='utf-8') == f'{len(events_sample())} events\n'


def test_text_export_rejects_an_empty_file_name() -> None:
    with pytest.raises(ValueError, match='file_name'):
        TextExport('', lambda events: '')


def test_factories_satisfy_the_export_protocol() -> None:
    assert isinstance(chapters_export(), Export)
    assert isinstance(subtitles_export(), Export)
    assert isinstance(walkthrough_export('Order Approval'), Export)


def test_exports_run_creates_the_directory_and_returns_paths_in_order(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'
    exports = [chapters_export(), subtitles_export(), walkthrough_export()]

    paths = exports_run(events_sample(), directory, exports)

    paths_expected = [
        directory / 'chapters.txt',
        directory / 'subtitles.vtt',
        directory / 'walkthrough.md',
    ]

    assert paths == paths_expected
    assert all(path.is_file() for path in paths)
