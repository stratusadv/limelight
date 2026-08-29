from __future__ import annotations

import json

from typing import TYPE_CHECKING

from limelight.export.cli import main

from fakes import FakeEncoder

if TYPE_CHECKING:
    from pathlib import Path


def demo_write(directory: Path, *, video: bool = True) -> None:
    directory.mkdir()

    events = [
        {'event': 'narrate', 'offset_ms': 0, 'title': 'Welcome'},
    ]

    payload = {'events': events}

    (directory / 'transcript.json').write_text(json.dumps(payload), encoding='utf-8')

    if video:
        (directory / 'video.mp4').write_bytes(b'')


def test_main_writes_the_text_exports_without_touching_the_encoder(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'
    encoder = FakeEncoder()

    demo_write(directory, video=False)

    exit_code = main([str(directory)], encoder=encoder.as_encoder())

    assert exit_code == 0
    assert (directory / 'chapters.txt').is_file()
    assert (directory / 'subtitles.vtt').is_file()
    assert (directory / 'walkthrough.md').is_file()
    assert encoder.runs == []


def test_main_subtitles_flag_burns_captions(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'
    encoder = FakeEncoder()

    demo_write(directory)

    exit_code = main([str(directory), '--subtitles'], encoder=encoder.as_encoder())

    assert exit_code == 0
    assert len(encoder.runs) == 1
    assert encoder.runs[0][:2] == ['-i', str(directory / 'video.mp4')]
    assert encoder.runs[0][-1] == str(directory / 'render.mp4')
    assert any(argument.startswith('subtitles=') for argument in encoder.runs[0])


def test_main_audio_flag_mixes_the_track(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'
    encoder = FakeEncoder()

    demo_write(directory)

    arguments = [str(directory), '--audio', str(directory / 'voice.wav')]
    exit_code = main(arguments, encoder=encoder.as_encoder())

    inputs_expected = ['-i', str(directory / 'video.mp4'), '-i', str(directory / 'voice.wav')]

    assert exit_code == 0
    assert encoder.runs[0][:4] == inputs_expected


def test_main_gif_flag_renders_gif(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'
    encoder = FakeEncoder()

    demo_write(directory)

    exit_code = main([str(directory), '--gif'], encoder=encoder.as_encoder())

    assert exit_code == 0
    assert encoder.runs[0][-1] == str(directory / 'video.gif')


def test_main_reaches_for_ffmpeg_when_no_encoder_is_given(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'

    demo_write(directory, video=False)

    assert main([str(directory)]) == 0
    assert (directory / 'walkthrough.md').is_file()
