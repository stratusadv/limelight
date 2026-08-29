from __future__ import annotations

import asyncio
import base64
import math
import threading
import time

from typing import TYPE_CHECKING, Protocol

from playwright.async_api import async_playwright

if TYPE_CHECKING:
    from collections.abc import Mapping

    from playwright.async_api import Browser, CDPSession
    from playwright.sync_api import Page

    from limelight.capture.sinks import FrameSink


FRAME_COUNT_MAX = 1_000_000
FRAME_FPS_DEFAULT = 60
FRAME_FPS_MAX = 240
FRAME_TICKS_LEAD_MS = 60_000
FRAME_TIMEOUT_SECONDS = 30

NAVIGATION_POLL_SECONDS = 0.02
NAVIGATION_SETTLE_SECONDS = 0.1

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
WAIT_SLICE_MS = 5

_renderers: dict[int, FrameRenderer] = {}


class FrameClock(Protocol):
    """A protocol for the clock a frame-paced demo advances its waits on."""

    def wait_ms(self, ms: float) -> None:
        """
        A method that holds until the timeline has advanced by a duration.

        :param ms: The duration to advance by.
        """

        ...


class _NavigationWatch:
    """
    A watch on the frames a page is loading.

    This class tracks the loads in flight so the renderer can hold its capture
    while a document is being replaced, because a frame requested mid-navigation
    comes back blank or times out.
    """

    def __init__(self) -> None:
        """The constructor for the _NavigationWatch class."""

        self._frames_loading: set[str] = set()
        self._settled_at = 0.0

    @property
    def in_progress(self) -> bool:
        """
        A property that reports whether a navigation is still under way.

        The watch stays in progress for a settling period after the last frame stops,
        because the first paint of the new document arrives after the load event and a
        frame captured before it shows the page half-drawn.

        :return: True if a load is in flight or still settling, False otherwise.
        """

        if self._frames_loading:
            return True

        return time.monotonic() < self._settled_at

    def _started(self, event: dict[str, object]) -> None:
        """
        A method that records a frame beginning to load.

        :param event: The event the browser reported.
        """

        self._frames_loading.add(str(event.get('frameId', '')))

    def _stopped(self, event: dict[str, object]) -> None:
        """
        A method that records a frame finishing its load.

        :param event: The event the browser reported.
        """

        self._frames_loading.discard(str(event.get('frameId', '')))

        if not self._frames_loading:
            self._settled_at = time.monotonic() + NAVIGATION_SETTLE_SECONDS

    async def watch(self, session: CDPSession) -> None:
        """
        A method that subscribes the watch to the page events of a session.

        :param session: The session the events are read from.
        """

        self._frames_loading.clear()

        session.on('Page.frameStartedLoading', self._started)
        session.on('Page.frameStoppedLoading', self._stopped)

        await session.send('Page.enable')


class FrameRenderer:
    """
    A capture that drives the browser one frame at a time.

    This class runs its own thread with its own asyncio loop and its own connection
    to the browser, and each frame is produced by asking the compositor for one at
    a timestamp the renderer chooses. The timeline is therefore the renderer's
    rather than the wall clock's, so a slow screenshot lengthens the recording
    instead of dropping a frame from it.
    """

    def __init__(
        self,
        page: Page,
        *,
        endpoint: str,
        fps: int = FRAME_FPS_DEFAULT,
        screenshot_format: str = SCREENSHOT_FORMAT_DEFAULT,
        screenshot_quality: int = SCREENSHOT_QUALITY_DEFAULT,
    ) -> None:
        """
        The constructor for the FrameRenderer class.

        :param page: The page the frames are captured from.
        :param endpoint: The URL of the debugging endpoint the capture connects over.
        :param fps: The frame rate the timeline advances at.
        :param screenshot_format: The image format each frame is captured in.
        :param screenshot_quality: The quality of each frame, where the format takes one.
        :raises ValueError: If the frame rate, the format, or the quality is out of range.
        """

        if fps < 1:
            message = f'fps must be positive: {fps}'
            raise ValueError(message)

        if fps > FRAME_FPS_MAX:
            message = f'fps must not exceed {FRAME_FPS_MAX}: {fps}'
            raise ValueError(message)

        if screenshot_format not in SCREENSHOT_FORMATS:
            options = ', '.join(SCREENSHOT_FORMATS)

            message = f'screenshot_format must be one of: {options} (got "{screenshot_format}")'
            raise ValueError(message)

        if screenshot_quality < 0:
            message = f'screenshot_quality must be non-negative: {screenshot_quality}'
            raise ValueError(message)

        if screenshot_quality > SCREENSHOT_QUALITY_MAX:
            message = (
                f'screenshot_quality must not exceed {SCREENSHOT_QUALITY_MAX}:'
                f' {screenshot_quality}'
            )

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
        self._ticks_last: dict[str, float] = {}

    @property
    def fps(self) -> int:
        """
        A property that exposes the frame rate the timeline advances at.

        :return: The frames per second.
        """

        return self._fps

    @property
    def frame_count(self) -> int:
        """
        A property that exposes how many frames have been written.

        :return: The number of frames written so far.
        """

        return self._frame_count

    @property
    def interval_ms(self) -> float:
        """
        A property that exposes the time one frame covers.

        :return: The milliseconds between frames.
        """

        return self._interval_ms

    @property
    def is_running(self) -> bool:
        """
        A property that reports whether the capture thread is running.

        :return: True if the thread is running, False otherwise.
        """

        return self._thread is not None

    def _error_raised(self) -> None:
        """
        A method that re-raises whatever killed the capture thread.

        The error is cleared as it is raised, so a failure surfaces once at the first
        call that notices it rather than at every call after.

        :raises RuntimeError: If the capture thread failed.
        """

        error = self._error

        if error is None:
            return

        self._error = None

        message = 'the frame renderer failed'
        raise RuntimeError(message) from error

    def _run(self) -> None:
        """
        A method that runs the capture loop on its own asyncio loop.

        The ready flag is set on failure as well as on the first frame, because the
        starting thread waits on it and would otherwise block until its timeout for a
        capture that has already died.
        """

        try:
            asyncio.run(self._render())
        except BaseException as exception:
            self._error = exception
            self._ready.set()

    async def _render(self) -> None:
        """
        A method that captures frames until the renderer is stopped.

        A frame is requested at each timestamp on the timeline and the last image is
        written again whenever the compositor returns nothing, so the recording keeps
        its frame rate through a repaint that produces no new pixels. A navigation
        pauses the loop, and the timeline is carried across the new document rather
        than restarted, so the two halves of the recording stay contiguous.

        :raises RuntimeError: If the renderer has no sink, or the frame count passes its maximum.
        """

        sink = self._sink

        if sink is None:
            message = 'the frame renderer has no sink'
            raise RuntimeError(message)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.connect_over_cdp(self._endpoint)
            target_id = self._target_id
            navigation = _NavigationWatch()
            session = await _session_attached(
                browser,
                target_id=target_id,
                endpoint=self._endpoint,
                navigation=navigation,
            )
            ticks = _ticks_seeded(self._ticks_last, target_id, self._interval_ms)
            image_last = b''

            navigated = False

            while not self._stop.is_set():
                if self._frame_count >= FRAME_COUNT_MAX:
                    message = f'the frame renderer passed {FRAME_COUNT_MAX} frames; aborting'
                    raise RuntimeError(message)

                if self._target_id != target_id:
                    await session.detach()

                    target_id = self._target_id

                    session = await _session_attached(
                        browser,
                        target_id=target_id,
                        endpoint=self._endpoint,
                        navigation=navigation,
                    )

                    ticks = _ticks_seeded(self._ticks_last, target_id, self._interval_ms)

                if navigation.in_progress:
                    navigated = True

                    await asyncio.sleep(NAVIGATION_POLL_SECONDS)

                    continue

                if navigated:
                    navigated = False
                    ticks = max(ticks + self._interval_ms, _ticks_now())

                await _real_time_awaited(ticks)

                image = await _frame_rendered(
                    session,
                    ticks=ticks,
                    interval_ms=self._interval_ms,
                    screenshot=self._screenshot,
                )

                self._ticks_last[target_id] = ticks
                ticks += self._interval_ms

                if image:
                    image_last = image

                if image_last:
                    sink.write(self._frame_count, image_last)

                self._frame_count += 1
                self._ready.set()

            await session.detach()
            await browser.close()

    def start(self, sink: FrameSink) -> None:
        """
        A method that opens the sink and starts the capture thread.

        The call blocks until the first frame is written, so a demo never records
        against a capture that has not attached yet.

        :param sink: The destination the frames are written to.
        :raises RuntimeError: If the renderer is already running, or no frame arrives in time.
        """

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
        """
        A method that stops the capture thread and closes the sink.

        The sink is closed whether or not the thread came down cleanly, because an
        encoder left with an open pipe never finishes writing its file. The capture
        failure is raised in preference to the sink failure, since a sink that could
        not be closed is usually the consequence of the thread that stopped feeding it.

        :raises RuntimeError: If the thread does not stop in time, the capture failed,
            or the sink could not be closed.
        """

        thread = self._thread

        if thread is None:
            return

        self._stop.set()
        thread.join(STOP_TIMEOUT_SECONDS)

        self._thread = None

        sink = self._sink
        self._sink = None

        try:
            if sink is not None:
                sink.close()
        finally:
            if thread.is_alive():
                message = f'the frame renderer did not stop within {STOP_TIMEOUT_SECONDS}s'
                raise RuntimeError(message)

            self._error_raised()

    def switch_page(self, page: Page) -> None:
        """
        A method that points the capture at a different page.

        :param page: The page later frames are captured from.
        """

        self._page = page
        self._target_id = _target_id_of(page)

    def wait_ms(self, ms: float) -> None:
        """
        A method that holds until the capture has advanced by a duration.

        The wait counts frames rather than time, so a demo waiting one second waits for
        the second of footage it asked for however long the machine takes to render it.
        A capture that stops producing frames raises rather than holding forever.

        :param ms: The duration to advance by.
        :raises RuntimeError: If the capture fails, or renders no frame for the stall timeout.
        """

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


def renderer_for(page: Page) -> FrameRenderer:
    """
    A function that looks up the renderer registered for a page.

    :param page: The page the renderer captures.
    :return: The renderer registered for the page.
    :raises LookupError: If no renderer is registered for the page.
    """

    renderer = _renderers.get(id(page))

    if renderer is None:
        message = (
            'no FrameRenderer is registered for the page;'
            ' the pytest plugin registers one in video mode'
        )

        raise LookupError(message)

    return renderer


def renderer_register(page: Page, renderer: FrameRenderer) -> None:
    """
    A function that registers a renderer against a page.

    :param page: The page the renderer captures.
    :param renderer: The renderer to register.
    """

    _renderers[id(page)] = renderer


def renderer_unregister(page: Page) -> None:
    """
    A function that drops the renderer registered for a page.

    :param page: The page whose renderer is dropped.
    """

    _renderers.pop(id(page), None)


async def _frame_rendered(
    session: CDPSession,
    *,
    ticks: float,
    interval_ms: float,
    screenshot: dict[str, object],
) -> bytes:
    """
    A function that asks the compositor for one frame.

    :param session: The session the frame is requested through.
    :param ticks: The timestamp the frame is rendered at.
    :param interval_ms: The time the frame covers.
    :param screenshot: The format and quality the frame is captured in.
    :return: The encoded image, or empty bytes if the compositor produced nothing.
    :raises TimeoutError: If the compositor does not answer within the frame timeout.
    """

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
    """
    A function that holds until real time catches up with the timeline.

    A capture that ran ahead of the wall clock would drive the page faster than its
    own animations and timers, so a timeline ahead of real time waits for it.

    :param ticks: The timestamp the next frame is rendered at.
    """

    ahead_ms = ticks - _ticks_now()

    if ahead_ms > 0:
        await asyncio.sleep(ahead_ms / 1000)


async def _session_attached(
    browser: Browser,
    *,
    target_id: str,
    endpoint: str,
    navigation: _NavigationWatch,
) -> CDPSession:
    """
    A function that attaches a session to the page carrying a target.

    The pages are searched rather than addressed directly, because a target opened
    by the demo appears in the connection a moment after the browser reports it, so
    the search is retried until it does.

    :param browser: The browser the session is opened on.
    :param target_id: The target the session must reach.
    :param endpoint: The URL of the debugging endpoint, used in the error message.
    :param navigation: The watch subscribed to the page events of the session.
    :return: The session attached to the page.
    :raises RuntimeError: If no page carries the target.
    """

    for _ in range(TARGET_ATTACH_ATTEMPT_COUNT_MAX):
        for context in browser.contexts:
            for page in context.pages:
                session = await context.new_cdp_session(page)
                target_info = await session.send('Target.getTargetInfo')

                if target_info['targetInfo']['targetId'] == target_id:
                    await navigation.watch(session)

                    return session

                await session.detach()

        await asyncio.sleep(TARGET_ATTACH_RETRY_SECONDS)

    message = f'no page with target {target_id} is reachable at {endpoint}'
    raise RuntimeError(message)


def _screenshot_parameters(screenshot_format: str, screenshot_quality: int) -> dict[str, object]:
    """
    A function that builds the screenshot options for a format.

    The quality is left out for PNG, because the format is lossless and the
    compositor rejects the option rather than ignoring it.

    :param screenshot_format: The image format each frame is captured in.
    :param screenshot_quality: The quality of each frame.
    :return: The screenshot options for the compositor.
    """

    if screenshot_format == 'png':
        return {'format': screenshot_format}

    return {'format': screenshot_format, 'quality': screenshot_quality}


def _target_id_of(page: Page) -> str:
    """
    A function that reads the target a page belongs to.

    :param page: The page to read.
    :return: The identifier of the target.
    """

    session = page.context.new_cdp_session(page)
    target_info = session.send('Target.getTargetInfo')

    session.detach()

    return str(target_info['targetInfo']['targetId'])


def _ticks_now() -> float:
    """
    A function that reads the current timeline position.

    The lead is added because the compositor rejects a frame timestamp that falls
    behind the timestamps it has already seen, and a browser that started before
    this process has a clock further along than a fresh monotonic reading.

    :return: The current position on the timeline.
    """

    return time.monotonic() * 1000 + FRAME_TICKS_LEAD_MS


def _ticks_seeded(
    ticks_by_target: Mapping[str, float],
    target_id: str,
    interval_ms: float,
) -> float:
    """
    A function that picks where the timeline resumes for a target.

    :param ticks_by_target: The last timestamp rendered for each target.
    :param target_id: The target the timeline is resuming for.
    :param interval_ms: The time one frame covers.
    :return: The timestamp the next frame is rendered at.
    """

    ticks_last = ticks_by_target.get(target_id)

    if ticks_last is None:
        return _ticks_now()

    return max(_ticks_now(), ticks_last + interval_ms)
