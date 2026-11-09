from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

from limelight.ffmpeg import Ffmpeg
from limelight.export import VoiceoverExport, voiceover_cues

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

    export = VoiceoverExport(synthesize, encoder=encoder.as_encoder())
    destination = export.export(events_sample(), tmp_path)

    texts = [text for text, _ in synthesized]
    paths = [path for _, path in synthesized]

    assert destination == tmp_path / 'voiceover.wav'
    assert texts == ['Order Approval Draft to approved.', 'Open the order Navigate to it.']
    assert paths == [tmp_path / 'voiceover-cue-00.wav', tmp_path / 'voiceover-cue-01.wav']
    assert encoder.runs[0][-1] == str(destination)


def test_export_rejects_events_without_narration(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []
    export = VoiceoverExport(lambda *_: None, encoder=FakeEncoder().as_encoder())

    with pytest.raises(ValueError, match='narrate'):
        export.export(events, tmp_path)


def test_export_runs_through_ffmpeg_when_no_encoder_is_given() -> None:
    export = VoiceoverExport(lambda *_: None)

    assert isinstance(export._encoder, Ffmpeg)


def test_export_rejects_an_empty_file_name() -> None:
    with pytest.raises(ValueError, match='file_name must not be empty'):
        VoiceoverExport(lambda *_: None, file_name=' ')


def test_export_rejects_a_cue_suffix_without_a_dot() -> None:
    with pytest.raises(ValueError, match='cue_suffix must start with a dot: wav'):
        VoiceoverExport(lambda *_: None, cue_suffix='wav')
