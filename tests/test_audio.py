from __future__ import annotations

import pytest

from pathlib import Path

from limelight.audio import ffmpeg_arguments_voiceover, voiceover_cues, voiceover_render


def events_sample() -> list[dict[str, object]]:
    return [
        {
            'event': 'title_card',
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


def test_arguments_delay_each_cue_then_mix() -> None:
    cues = [
        (0, Path('cue-00.wav')),
        (1500, Path('cue-01.wav')),
    ]

    arguments = ffmpeg_arguments_voiceover(cues, Path('voiceover.wav'))

    filter_graph = arguments[arguments.index('-filter_complex') + 1]

    assert arguments[:4] == ['-i', 'cue-00.wav', '-i', 'cue-01.wav']
    assert '[0]adelay=0|0[voice0]' in filter_graph
    assert '[1]adelay=1500|1500[voice1]' in filter_graph
    assert 'amix=inputs=2:normalize=0[voiceover]' in filter_graph
    assert arguments[-1] == 'voiceover.wav'


def test_arguments_reject_empty_cues() -> None:
    with pytest.raises(ValueError, match='cues'):
        ffmpeg_arguments_voiceover([], Path('voiceover.wav'))


def test_arguments_reject_negative_offset() -> None:
    cues = [(-1, Path('cue-00.wav'))]

    with pytest.raises(ValueError, match='offset_ms'):
        ffmpeg_arguments_voiceover(cues, Path('voiceover.wav'))


def test_render_synthesizes_each_cue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs: list[list[str]] = []

    monkeypatch.setattr('limelight.audio.ffmpeg_run', runs.append)

    synthesized: list[tuple[str, Path]] = []

    def synthesize(text: str, path: Path) -> None:
        request = (text, path)
        synthesized.append(request)

    destination = tmp_path / 'voiceover.wav'
    result = voiceover_render(events_sample(), synthesize, destination)

    texts = [text for text, _ in synthesized]
    paths = [path for _, path in synthesized]

    assert result == destination
    assert texts == ['Order Approval Draft to approved.', 'Open the order Navigate to it.']
    assert paths == [tmp_path / 'voiceover-cue-00.wav', tmp_path / 'voiceover-cue-01.wav']
    assert len(runs) == 1


def test_render_rejects_events_without_narration(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []

    with pytest.raises(ValueError, match='narrate'):
        voiceover_render(events, lambda text, path: None, tmp_path / 'voiceover.wav')
