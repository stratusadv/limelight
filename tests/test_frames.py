from __future__ import annotations

import threading

import pytest

from typing import TYPE_CHECKING, cast, override

from limelight.frames import (
    LAUNCH_ARGUMENTS_FRAME_CONTROL,
    WAIT_SLICE_MS,
    DirectorySink,
    _NavigationWatch,
    FrameRenderer,
    VideoSink,
    endpoint_free,
    endpoint_port,
    launch_arguments_frame_control,
    renderer_for,
    renderer_register,
    renderer_unregister,
)

from fakes import FakePage

if TYPE_CHECKING:
    from pathlib import Path

    from playwright.sync_api import Page


class TickingPage(FakePage):
    def __init__(self, renderer_holder: list[FrameRenderer]) -> None:
        super().__init__()

        self._renderer_holder = renderer_holder

    @override
    def wait_for_timeout(self, ms: float) -> None:
        super().wait_for_timeout(ms)

        self._renderer_holder[0]._frame_count += 1


class FakeProcess:
    def __init__(self) -> None:
        self.stdin = FakeStdin()
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode


class FakeStdin:
    def __init__(self) -> None:
        self.closed = False
        self.written: list[bytes] = []

    def close(self) -> None:
        self.closed = True

    def write(self, data: bytes) -> None:
        self.written.append(data)


def renderer_build(page: FakePage | None = None) -> FrameRenderer:
    page = page if page is not None else FakePage()

    return FrameRenderer(cast('Page', page), endpoint='http://127.0.0.1:9333')


def test_fps_must_be_in_range() -> None:
    with pytest.raises(ValueError, match='fps'):
        FrameRenderer(FakePage().as_page(), endpoint='http://127.0.0.1:9333', fps=0)


def test_screenshot_format_must_be_known() -> None:
    with pytest.raises(ValueError, match='screenshot_format'):
        FrameRenderer(FakePage().as_page(), endpoint='http://127.0.0.1:9333', screenshot_format='bmp')


def test_screenshot_quality_must_be_in_range() -> None:
    with pytest.raises(ValueError, match='screenshot_quality'):
        FrameRenderer(FakePage().as_page(), endpoint='http://127.0.0.1:9333', screenshot_quality=101)


def test_interval_follows_fps() -> None:
    renderer = FrameRenderer(FakePage().as_page(), endpoint='http://127.0.0.1:9333', fps=50)

    assert renderer.fps == 50
    assert renderer.interval_ms == 20


def test_wait_ms_sleeps_for_real_when_not_rendering() -> None:
    page = FakePage()
    renderer = renderer_build(page)

    renderer.wait_ms(250)

    assert page.waits_ms == [250]


def test_wait_ms_ignores_non_positive_durations() -> None:
    page = FakePage()
    renderer = renderer_build(page)

    renderer.wait_ms(0)
    renderer.wait_ms(-5)

    assert page.waits_ms == []


def test_wait_ms_counts_frames_while_rendering() -> None:
    holder: list[FrameRenderer] = []
    page = TickingPage(holder)
    renderer = renderer_build(page)

    holder.append(renderer)
    renderer._thread = threading.Thread(target=lambda: None)

    renderer.wait_ms(100)

    assert page.waits_ms == [WAIT_SLICE_MS] * 6
    assert renderer.frame_count == 6


def test_wait_ms_raises_the_thread_error() -> None:
    holder: list[FrameRenderer] = []
    page = TickingPage(holder)
    renderer = renderer_build(page)

    holder.append(renderer)
    renderer._thread = threading.Thread(target=lambda: None)
    renderer._error = RuntimeError('boom')

    with pytest.raises(RuntimeError, match='frame renderer failed'):
        renderer.wait_ms(100)


def test_stop_without_start_is_a_no_op() -> None:
    renderer = renderer_build()

    renderer.stop()

    assert renderer.is_running is False


def test_directory_sink_writes_numbered_frames(tmp_path: Path) -> None:
    sink = DirectorySink(tmp_path / 'frames')

    sink.open()
    sink.write(0, b'first')
    sink.write(1, b'second')
    sink.close()

    assert (tmp_path / 'frames' / 'frame-000000.png').read_bytes() == b'first'
    assert (tmp_path / 'frames' / 'frame-000001.png').read_bytes() == b'second'


def test_video_sink_pipes_frames_into_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    process = FakeProcess()
    commands: list[list[str]] = []

    def start_stub(arguments: list[str]) -> FakeProcess:
        commands.append(arguments)

        return process

    monkeypatch.setattr('limelight.frames.ffmpeg_process_start', start_stub)

    sink = VideoSink(tmp_path / 'out' / 'video.mp4', fps=30)

    sink.open()
    sink.write(0, b'png')
    sink.close()

    assert (tmp_path / 'out').is_dir()
    assert commands[0][:4] == ['-f', 'image2pipe', '-framerate', '30']
    assert process.stdin.written == [b'png']
    assert process.stdin.closed is True


def test_video_sink_reports_ffmpeg_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    process = FakeProcess()
    process.returncode = 1

    monkeypatch.setattr('limelight.frames.ffmpeg_process_start', lambda arguments: process)

    sink = VideoSink(tmp_path / 'video.mp4')

    sink.open()

    with pytest.raises(RuntimeError, match='status 1'):
        sink.close()


def test_video_sink_refuses_writes_before_open(tmp_path: Path) -> None:
    sink = VideoSink(tmp_path / 'video.mp4')

    with pytest.raises(RuntimeError, match='not open'):
        sink.write(0, b'png')


def test_endpoint_free_is_local_with_a_port() -> None:
    endpoint = endpoint_free()

    assert endpoint.startswith('http://127.0.0.1:')
    assert endpoint_port(endpoint) > 0


def test_endpoint_port_requires_a_port() -> None:
    with pytest.raises(ValueError, match='port'):
        endpoint_port('http://127.0.0.1')


def test_launch_arguments_carry_frame_control_scale_and_the_port() -> None:
    arguments = launch_arguments_frame_control('http://127.0.0.1:9333', device_scale_factor=2)

    assert arguments[:-2] == list(LAUNCH_ARGUMENTS_FRAME_CONTROL)
    assert arguments[-2:] == ['--force-device-scale-factor=2', '--remote-debugging-port=9333']


def test_launch_arguments_reject_a_zero_scale_factor() -> None:
    with pytest.raises(ValueError, match='device_scale_factor'):
        launch_arguments_frame_control('http://127.0.0.1:9333', device_scale_factor=0)


def test_registry_maps_a_page_to_its_renderer() -> None:
    page = FakePage().as_page()
    renderer = renderer_build()

    assert renderer_for(page) is None

    renderer_register(page, renderer)

    assert renderer_for(page) is renderer

    renderer_unregister(page)

    assert renderer_for(page) is None


def test_navigation_watch_pauses_until_every_frame_stops_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    watch = _NavigationWatch()
    clock = iter([100.0, 100.0, 100.0, 100.2])

    monkeypatch.setattr('limelight.frames.time.monotonic', lambda: next(clock))

    assert watch.in_progress is False

    watch._started({'frameId': 'main'})
    watch._started({'frameId': 'child'})

    assert watch.in_progress is True

    watch._stopped({'frameId': 'child'})

    assert watch.in_progress is True

    watch._stopped({'frameId': 'main'})

    assert watch.in_progress is True
    assert watch.in_progress is False
