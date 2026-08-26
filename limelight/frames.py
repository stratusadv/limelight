from __future__ import annotations

import asyncio
import base64
import math
import socket
import threading
import time

from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

from limelight.video import ffmpeg_arguments_frames, ffmpeg_process_start

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import Popen

    from playwright.async_api import Browser, CDPSession
    from playwright.sync_api import Page


ENDPOINT_HOST = '127.0.0.1'

FRAME_FPS_DEFAULT = 60
FRAME_FPS_MAX = 240
FRAME_TICKS_LEAD_MS = 60_000
FRAME_TIMEOUT_SECONDS = 30

NAVIGATION_POLL_SECONDS = 0.02
NAVIGATION_SETTLE_SECONDS = 0.1

LAUNCH_ARGUMENTS_FRAME_CONTROL = (
    '--disable-checker-imaging',
    '--disable-image-animation-resync',
    '--disable-threaded-animation',
    '--disable-threaded-scrolling',
    '--enable-begin-frame-control',
    '--hide-scrollbars',
    '--run-all-compositor-stages-before-draw',
)

READY_TIMEOUT_SECONDS = 30
SCREENSHOT_FORMATS = ('jpeg', 'png', 'webp')
SCREENSHOT_FORMAT_DEFAULT = 'jpeg'
SCREENSHOT_QUALITY_DEFAULT = 100
SCREENSHOT_QUALITY_MAX = 100
STALL_SECONDS_MAX = 120
STOP_TIMEOUT_SECONDS = 120
TARGET_ATTACH_ATTEMPT_COUNT_MAX = 50
TARGET_ATTACH_RETRY_SECONDS = 0.1
THREAD_NAME = 'limelight-frames'
VIDEO_FILE_NAME = 'video.mp4'
WAIT_SLICE_MS = 5

_renderers: dict[int, FrameRenderer] = {}
_ticks_last: dict[str, float] = {}


class FrameClock(Protocol):
    def wait_ms(self, ms: float) -> None: ...


class FrameSink(Protocol):
    def close(self) -> None: ...

    def open(self) -> None: ...

    def write(self, index: int, png: bytes) -> None: ...


class DirectorySink:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def close(self) -> None:
        pass

    def open(self) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)

    def write(self, index: int, png: bytes) -> None:
        (self._directory / f'frame-{index:06d}.png').write_bytes(png)


class VideoSink:
    def __init__(self, destination: Path, *, fps: int = FRAME_FPS_DEFAULT) -> None:
        self._destination = destination
        self._fps = fps
        self._process: Popen[bytes] | None = None

    def close(self) -> None:
        process = self._process

        if process is None:
            return

        self._process = None

        if process.stdin is not None:
            process.stdin.close()

        return_code = process.wait(timeout=STOP_TIMEOUT_SECONDS)

        if return_code != 0:
            message = f'ffmpeg exited with status {return_code} while writing {self._destination}'
            raise RuntimeError(message)

    def open(self) -> None:
        self._destination.parent.mkdir(parents=True, exist_ok=True)

        self._process = ffmpeg_process_start(ffmpeg_arguments_frames(self._destination, fps=self._fps))

    def write(self, index: int, png: bytes) -> None:  # noqa: ARG002
        process = self._process

        if process is None or process.stdin is None:
            message = f'the video sink for {self._destination} is not open'
            raise RuntimeError(message)

        process.stdin.write(png)


class _NavigationWatch:
    def __init__(self) -> None:
        self._frames_loading: set[str] = set()
        self._settled_at = 0.0

    @property
    def in_progress(self) -> bool:
        if self._frames_loading:
            return True

        return time.monotonic() < self._settled_at

    def _started(self, event: dict[str, object]) -> None:
        self._frames_loading.add(str(event.get('frameId', '')))

    def _stopped(self, event: dict[str, object]) -> None:
        self._frames_loading.discard(str(event.get('frameId', '')))

        if not self._frames_loading:
            self._settled_at = time.monotonic() + NAVIGATION_SETTLE_SECONDS

    async def watch(self, session: CDPSession) -> None:
        self._frames_loading.clear()

        session.on('Page.frameStartedLoading', self._started)
        session.on('Page.frameStoppedLoading', self._stopped)

        await session.send('Page.enable')


class FrameRenderer:
    def __init__(
        self,
        page: Page,
        *,
        endpoint: str,
        fps: int = FRAME_FPS_DEFAULT,
        screenshot_format: str = SCREENSHOT_FORMAT_DEFAULT,
        screenshot_quality: int = SCREENSHOT_QUALITY_DEFAULT,
    ) -> None:
        if fps < 1 or fps > FRAME_FPS_MAX:
            message = f'fps must fall between 1 and {FRAME_FPS_MAX}: {fps}'
            raise ValueError(message)

        if screenshot_format not in SCREENSHOT_FORMATS:
            options = ', '.join(SCREENSHOT_FORMATS)

            message = f'screenshot_format must be one of: {options} (got "{screenshot_format}")'
            raise ValueError(message)

        if screenshot_quality < 0 or screenshot_quality > SCREENSHOT_QUALITY_MAX:
            message = f'screenshot_quality must fall between 0 and {SCREENSHOT_QUALITY_MAX}: {screenshot_quality}'
            raise ValueError(message)

        self._endpoint = endpoint
        self._error: BaseException | None = None
        self._fps = fps
        self._frame_count = 0
        self._interval_ms = 1000 / fps
        self._page = page
        self._ready = threading.Event()
        self._screenshot = _screenshot_parameters(screenshot_format, screenshot_quality)
        self._sink: FrameSink | None = None
        self._stop = threading.Event()
        self._target_id = ''
        self._thread: threading.Thread | None = None

    @property
    def fps(self) -> int:
        return self._fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def interval_ms(self) -> float:
        return self._interval_ms

    @property
    def is_running(self) -> bool:
        return self._thread is not None

    def _error_raised(self) -> None:
        error = self._error

        if error is None:
            return

        self._error = None

        message = 'the frame renderer failed'
        raise RuntimeError(message) from error

    def _run(self) -> None:
        try:
            asyncio.run(self._render())
        except BaseException as exception:  # noqa: BLE001
            self._error = exception
            self._ready.set()

    async def _render(self) -> None:
        sink = self._sink

        if sink is None:
            message = 'the frame renderer has no sink'
            raise RuntimeError(message)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.connect_over_cdp(self._endpoint)
            target_id = self._target_id
            navigation = _NavigationWatch()
            session = await _session_attached(browser, target_id, self._endpoint, navigation)
            ticks = _ticks_seeded(target_id, self._interval_ms)
            png_last = b''

            while not self._stop.is_set():
                if self._target_id != target_id:
                    await session.detach()

                    target_id = self._target_id
                    session = await _session_attached(browser, target_id, self._endpoint, navigation)
                    ticks = _ticks_seeded(target_id, self._interval_ms)

                if navigation.in_progress:
                    await asyncio.sleep(NAVIGATION_POLL_SECONDS)

                    continue

                await _real_time_awaited(ticks)

                png = await _frame_rendered(session, ticks, self._interval_ms, self._screenshot)

                _ticks_last[target_id] = ticks
                ticks += self._interval_ms

                if png:
                    png_last = png

                if png_last:
                    sink.write(self._frame_count, png_last)

                self._frame_count += 1
                self._ready.set()

            await session.detach()
            await browser.close()

    def retarget(self, page: Page) -> None:
        self._page = page
        self._target_id = _target_id_of(page)

    def start(self, sink: FrameSink) -> None:
        if self._thread is not None:
            message = 'the frame renderer is already running'
            raise RuntimeError(message)

        self._target_id = _target_id_of(self._page)

        sink.open()

        self._error = None
        self._sink = sink

        self._ready.clear()
        self._stop.clear()

        thread = threading.Thread(target=self._run, name=THREAD_NAME, daemon=True)
        self._thread = thread

        thread.start()

        if not self._ready.wait(READY_TIMEOUT_SECONDS):
            self.stop()

            message = f'the frame renderer produced no frame within {READY_TIMEOUT_SECONDS}s'
            raise RuntimeError(message)

        self._error_raised()

    def stop(self) -> None:
        thread = self._thread

        if thread is None:
            return

        self._stop.set()
        thread.join(STOP_TIMEOUT_SECONDS)

        self._thread = None

        sink = self._sink
        self._sink = None

        if sink is not None:
            sink.close()

        if thread.is_alive():
            message = f'the frame renderer did not stop within {STOP_TIMEOUT_SECONDS}s'
            raise RuntimeError(message)

        self._error_raised()

    def wait_ms(self, ms: float) -> None:
        if ms <= 0:
            return

        if self._thread is None:
            self._page.wait_for_timeout(ms)

            return

        frame_count_target = self._frame_count + max(1, math.ceil(ms / self._interval_ms))
        frame_count_seen = self._frame_count
        stalled_since = time.monotonic()

        while self._frame_count < frame_count_target:
            self._error_raised()

            if self._frame_count != frame_count_seen:
                frame_count_seen = self._frame_count
                stalled_since = time.monotonic()
            elif time.monotonic() - stalled_since > STALL_SECONDS_MAX:
                message = f'no frame was rendered for {STALL_SECONDS_MAX}s'
                raise RuntimeError(message)

            self._page.wait_for_timeout(WAIT_SLICE_MS)


def endpoint_free() -> str:
    with socket.socket() as sock:
        sock.bind((ENDPOINT_HOST, 0))

        port = sock.getsockname()[1]

    return f'http://{ENDPOINT_HOST}:{port}'


def endpoint_port(endpoint: str) -> int:
    port = urlsplit(endpoint).port

    if port is None:
        message = f'the endpoint carries no port: {endpoint}'
        raise ValueError(message)

    return port


def launch_arguments_frame_control(endpoint: str, *, device_scale_factor: int = 1) -> list[str]:
    if device_scale_factor < 1:
        message = f'device_scale_factor must be positive: {device_scale_factor}'
        raise ValueError(message)

    return [
        *LAUNCH_ARGUMENTS_FRAME_CONTROL,
        f'--force-device-scale-factor={device_scale_factor}',
        f'--remote-debugging-port={endpoint_port(endpoint)}',
    ]


def renderer_for(page: Page) -> FrameRenderer | None:
    return _renderers.get(id(page))


def renderer_register(page: Page, renderer: FrameRenderer) -> None:
    _renderers[id(page)] = renderer


def renderer_unregister(page: Page) -> None:
    _renderers.pop(id(page), None)


async def _frame_rendered(
    session: CDPSession,
    ticks: float,
    interval_ms: float,
    screenshot: dict[str, object],
) -> bytes:
    parameters = {
        'frameTimeTicks': ticks,
        'interval': interval_ms,
        'noDisplayUpdates': False,
        'screenshot': screenshot,
    }

    result = await asyncio.wait_for(
        session.send('HeadlessExperimental.beginFrame', parameters),
        timeout=FRAME_TIMEOUT_SECONDS,
    )

    data = result.get('screenshotData')

    if not data:
        return b''

    return base64.b64decode(data)


async def _real_time_awaited(ticks: float) -> None:
    ahead_ms = ticks - _ticks_now()

    if ahead_ms > 0:
        await asyncio.sleep(ahead_ms / 1000)


async def _session_attached(
    browser: Browser,
    target_id: str,
    endpoint: str,
    navigation: _NavigationWatch,
) -> CDPSession:
    for _ in range(TARGET_ATTACH_ATTEMPT_COUNT_MAX):
        for context in browser.contexts:
            for page in context.pages:
                session = await context.new_cdp_session(page)
                info = await session.send('Target.getTargetInfo')

                if info['targetInfo']['targetId'] == target_id:
                    await navigation.watch(session)

                    return session

                await session.detach()

        await asyncio.sleep(TARGET_ATTACH_RETRY_SECONDS)

    message = f'no page with target {target_id} is reachable at {endpoint}'
    raise RuntimeError(message)


def _ticks_now() -> float:
    return time.monotonic() * 1000 + FRAME_TICKS_LEAD_MS


def _ticks_seeded(target_id: str, interval_ms: float) -> float:
    ticks_last = _ticks_last.get(target_id)

    if ticks_last is None:
        return _ticks_now()

    return max(_ticks_now(), ticks_last + interval_ms)


def _screenshot_parameters(screenshot_format: str, screenshot_quality: int) -> dict[str, object]:
    if screenshot_format == 'png':
        return {'format': screenshot_format}

    return {'format': screenshot_format, 'quality': screenshot_quality}


def _target_id_of(page: Page) -> str:
    session = page.context.new_cdp_session(page)
    info = session.send('Target.getTargetInfo')

    session.detach()

    return str(info['targetInfo']['targetId'])
