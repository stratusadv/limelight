from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

from limelight.export.voiceover import VoiceoverExport, voiceover_cues

from fakes import FakeEncoder

if TYPE_CHECKING:
    from pathlib import Path


def events_sample() -> list[dict[str, object]]:
    return [
        {
            'event': 'title',
            'offset_ms': 0,
            'title': 'Order Approval',
            'kicker': 'Chapter One',
            'subtitle': 'Draft to approved.',
        },
        {
            'event': 'narrate',
            'offset_ms': 2000,
            'title': 'Open the order',
            'body': 'Navigate to it.',
        },
        {
            'event': 'spotlight',
            'offset_ms': 4000,
            'label': 'Click "Orders"',
        },
    ]


def test_cues_come_from_narration_events() -> None:
    cues = voiceover_cues(events_sample())

    assert cues == [
        (0, 'Order Approval Draft to approved.'),
        (2000, 'Open the order Navigate to it.'),
    ]


def test_cues_skip_untitled_events() -> None:
    events: list[dict[str, object]] = [
        {'event': 'narrate', 'offset_ms': 0, 'title': ''},
    ]

    assert voiceover_cues(events) == []


def test_export_synthesizes_each_cue_then_mixes(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    synthesized: list[tuple[str, Path]] = []

    def synthesize(text: str, path: Path) -> None:
        request = (text, path)
        synthesized.append(request)

    export = VoiceoverExport(encoder.as_encoder(), synthesize)
    destination = export.export(events_sample(), tmp_path)

    texts = [text for text, _ in synthesized]
    paths = [path for _, path in synthesized]

    assert destination == tmp_path / 'voiceover.wav'
    assert texts == ['Order Approval Draft to approved.', 'Open the order Navigate to it.']
    assert paths == [tmp_path / 'voiceover-cue-00.wav', tmp_path / 'voiceover-cue-01.wav']
    assert encoder.runs[0][-1] == str(destination)


def test_export_rejects_events_without_narration(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []
    export = VoiceoverExport(FakeEncoder().as_encoder(), lambda text, path: None)

    with pytest.raises(ValueError, match='narrate'):
        export.export(events, tmp_path)
