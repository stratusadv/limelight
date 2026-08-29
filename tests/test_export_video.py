from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

from limelight.export.video import GifExport, VideoExport

from fakes import FakeEncoder

if TYPE_CHECKING:
    from pathlib import Path


def test_video_export_encodes_beside_the_source(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    (tmp_path / 'video.mp4').write_bytes(b'')

    export = VideoExport(encoder.as_encoder(), subtitles=tmp_path / 'subtitles.vtt')
    destination = export.export([], tmp_path)

    assert destination == tmp_path / 'render.mp4'
    assert encoder.runs[0][:2] == ['-i', str(tmp_path / 'video.mp4')]
    assert encoder.runs[0][-1] == str(destination)
    assert '-vf' in encoder.runs[0]


def test_video_export_requires_the_source(tmp_path: Path) -> None:
    export = VideoExport(FakeEncoder().as_encoder())

    with pytest.raises(FileNotFoundError, match=r'video\.mp4'):
        export.export([], tmp_path)


def test_gif_export_encodes_beside_the_source(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    (tmp_path / 'video.mp4').write_bytes(b'')

    destination = GifExport(encoder.as_encoder(), fps=10, width=640).export([], tmp_path)

    assert destination == tmp_path / 'video.gif'
    assert 'fps=10,scale=640:-1:flags=lanczos' in encoder.runs[0][3]


def test_gif_export_refuses_a_non_positive_fps() -> None:
    encoder = FakeEncoder()

    with pytest.raises(ValueError, match='fps must be positive: 0'):
        GifExport(encoder.as_encoder(), fps=0)


def test_gif_export_refuses_a_non_positive_width() -> None:
    encoder = FakeEncoder()

    with pytest.raises(ValueError, match='width must be positive: 0'):
        GifExport(encoder.as_encoder(), width=0)
