from __future__ import annotations

import json
import os

import pytest

from pathlib import Path

from limelight.render import main, trim_lead_ms_detect, video_locate


def transcript_write(directory: Path, payload: dict[str, object]) -> Path:
    path = directory / 'transcript.json'

    path.write_text(json.dumps(payload), encoding='utf-8')

    return path


def test_video_locate_prefers_newest(tmp_path: Path) -> None:
    older = tmp_path / 'older.webm'
    newer = tmp_path / 'videos' / 'newer.webm'

    older.write_bytes(b'')
    newer.parent.mkdir()
    newer.write_bytes(b'')

    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    assert video_locate(tmp_path) == newer


def test_video_locate_rejects_missing_video(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match='webm'):
        video_locate(tmp_path)


def test_trim_detect_without_epoch_returns_zero() -> None:
    assert trim_lead_ms_detect(Path('demo.webm'), {}) == 0


def test_trim_detect_without_ffprobe_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.render.shutil.which', lambda name: None)

    payload: dict[str, object] = {'started_at_epoch_ms': 5000}

    assert trim_lead_ms_detect(Path('demo.webm'), payload) == 0


def test_trim_detect_computes_lead(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.render.shutil.which', lambda name: '/usr/bin/ffprobe')
    monkeypatch.setattr('limelight.render.video_started_at_epoch_ms', lambda video: 3000)

    payload: dict[str, object] = {'started_at_epoch_ms': 5000}

    assert trim_lead_ms_detect(Path('demo.webm'), payload) == 2000


def test_main_writes_exports_then_renders_video(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / 'demo'
    directory.mkdir()

    events = [
        {'event': 'narrate', 'offset_ms': 0, 'title': 'Welcome'},
    ]
    payload: dict[str, object] = {'events': events, 'started_at_epoch_ms': 100}

    transcript_write(directory, payload)

    video = directory / 'demo.webm'
    video.write_bytes(b'')

    rendered: dict[str, object] = {}

    def render_mp4_stub(
        source: Path,
        destination: Path | None = None,
        *,
        audio: Path | None = None,
        subtitles: Path | None = None,
        trim_lead_ms: int = 0,
    ) -> Path:
        rendered['mp4'] = (source, audio, subtitles, trim_lead_ms)

        return source.with_suffix('.mp4')

    monkeypatch.setattr('limelight.render.render_mp4', render_mp4_stub)
    monkeypatch.setattr('limelight.render.render_gif', lambda source: rendered.setdefault('gif', source))
    monkeypatch.setattr('limelight.render.shutil.which', lambda name: None)

    arguments = [str(directory)]
    exit_code = main(arguments)

    assert exit_code == 0
    assert (directory / 'chapters.txt').is_file()
    assert (directory / 'subtitles.vtt').is_file()
    assert (directory / 'walkthrough.md').is_file()
    assert rendered['mp4'] == (video, None, directory / 'subtitles.vtt', 0)
    assert 'gif' not in rendered


def test_main_gif_flag_renders_gif(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / 'demo'
    directory.mkdir()

    payload: dict[str, object] = {'events': [], 'started_at_epoch_ms': 100}

    transcript_write(directory, payload)

    video = directory / 'demo.webm'
    video.write_bytes(b'')

    rendered: dict[str, object] = {}

    monkeypatch.setattr('limelight.render.render_mp4', lambda source, **kwargs: source.with_suffix('.mp4'))
    monkeypatch.setattr('limelight.render.render_gif', lambda source: rendered.setdefault('gif', source))
    monkeypatch.setattr('limelight.render.shutil.which', lambda name: None)

    arguments = [str(directory), '--gif']
    exit_code = main(arguments)

    assert exit_code == 0
    assert rendered['gif'] == video
