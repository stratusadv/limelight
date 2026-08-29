from __future__ import annotations

import pytest

from typing_extensions import override

from subprocess import TimeoutExpired
from typing import TYPE_CHECKING, cast

from limelight.capture.sinks import STOP_TIMEOUT_SECONDS, DirectorySink, VideoSink

from fakes import FakeEncoder, FakeProcess

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


class HangingProcess(FakeProcess):
    def __init__(self) -> None:
        super().__init__()

        self.killed = False

    def kill(self) -> None:
        self.killed = True

    @override
    def wait(self, timeout: float | None = None) -> int:
        if timeout is not None and not self.killed:
            command = 'ffmpeg'
            raise TimeoutExpired(command, timeout)

        return self.returncode


def test_directory_sink_writes_numbered_frames(tmp_path: Path) -> None:
    sink = DirectorySink(tmp_path / 'frames')

    sink.open()
    sink.write(0, b'first')
    sink.write(1, b'second')
    sink.close()

    assert (tmp_path / 'frames' / 'frame-000000.png').read_bytes() == b'first'
    assert (tmp_path / 'frames' / 'frame-000001.png').read_bytes() == b'second'


def test_video_sink_pipes_frames_into_the_encoder(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    sink = VideoSink(tmp_path / 'out' / 'video.mp4', encoder.as_encoder(), fps=30)

    sink.open()
    sink.write(0, b'png')
    sink.close()

    assert (tmp_path / 'out').is_dir()
    assert encoder.pipes[0][:4] == ['-f', 'image2pipe', '-framerate', '30']
    assert encoder.process.stdin.written == [b'png']
    assert encoder.process.stdin.closed is True


def test_video_sink_reports_encoder_failure(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    encoder.process.returncode = 1

    sink = VideoSink(tmp_path / 'video.mp4', encoder.as_encoder())

    sink.open()

    with pytest.raises(RuntimeError, match='status 1'):
        sink.close()


def test_video_sink_refuses_writes_before_open(tmp_path: Path) -> None:
    sink = VideoSink(tmp_path / 'video.mp4', FakeEncoder().as_encoder())

    with pytest.raises(RuntimeError, match='not open'):
        sink.write(0, b'png')


def test_directory_sink_refuses_a_suffix_without_a_dot(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='suffix must start with a dot: png'):
        DirectorySink(tmp_path / 'frames', suffix='png')


def test_closing_a_video_sink_that_never_opened_does_nothing(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    sink = VideoSink(tmp_path / 'video.mp4', encoder.as_encoder())

    sink.close()

    assert encoder.pipes == []


def test_writing_to_a_closed_video_sink_raises(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    sink = VideoSink(tmp_path / 'video.mp4', encoder.as_encoder())

    with pytest.raises(RuntimeError, match='is not open'):
        sink.write(0, b'frame')


def test_writing_without_a_pipe_into_the_encoder_raises(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    cast('Any', encoder.process).stdin = None

    sink = VideoSink(tmp_path / 'video.mp4', encoder.as_encoder())

    sink.open()

    with pytest.raises(RuntimeError, match='has no pipe into the encoder'):
        sink.write(0, b'frame')


def test_video_sink_carries_the_encoder_settings(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    sink = VideoSink(
        tmp_path / 'video.mp4',
        encoder.as_encoder(),
        crf=28,
        fps=30,
        preset='veryfast',
    )

    sink.open()

    arguments = encoder.pipes[0]

    assert arguments[arguments.index('-crf') + 1] == '28'
    assert arguments[arguments.index('-preset') + 1] == 'veryfast'
    assert arguments[arguments.index('-framerate') + 1] == '30'


def test_a_hung_encoder_is_killed_rather_than_left_behind(tmp_path: Path) -> None:
    encoder = FakeEncoder()
    encoder.process = HangingProcess()

    sink = VideoSink(tmp_path / 'out' / 'video.mp4', encoder.as_encoder(), fps=30)

    sink.open()
    sink.write(0, b'frame')

    with pytest.raises(RuntimeError, match=f'did not finish within {STOP_TIMEOUT_SECONDS}s'):
        sink.close()

    assert encoder.process.killed is True
