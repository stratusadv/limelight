from __future__ import annotations

import asyncio
import base64
import math
import threading
import time

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Protocol

from playwright.async_api import async_playwright

from limelight.errors import RenderError
from limelight.javascript import script
from limelight.limits import FRAME_COUNT_MAX

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Literal

    from playwright.async_api import Browser, CDPSession
    from playwright.sync_api import Page

    from limelight.capture.sinks import FrameSink

    ColorScheme = Literal['dark', 'light']


COLOR_SCHEME_DARK_SCRIPT = script('color_scheme_dark.js')
FRAME_FPS_DEFAULT = 60
FRAME_FPS_MAX = 240
FRAME_TIMEOUT_SECONDS = 30

NAVIGATION_SETTLE_SECONDS = 0.1

READY_TIMEOUT_SECONDS = 30
RENDER_STEP_COUNT_MAX = FRAME_COUNT_MAX * 2
SCREENSHOT_FORMATS = ('jpeg', 'png', 'webp')
SCREENSHOT_FORMAT_DEFAULT = 'jpeg'
SCREENSHOT_QUALITY_DEFAULT = 100
SCREENSHOT_QUALITY_MAX = 100
STALL_SECONDS_MAX = 120
STOP_TIMEOUT_SECONDS = 120
TARGET_ATTACH_ATTEMPT_COUNT_MAX = 50
TARGET_ATTACH_RETRY_SECONDS = 0.1
THREAD_NAME = 'limelight-frames'
VIRTUAL_TIME_STARVATION_COUNT_MAX = 1000
WAIT_SLICE_MS = 5
WAIT_SLICE_COUNT_PER_FRAME_MAX = math.ceil(STALL_SECONDS_MAX * 1000 / WAIT_SLICE_MS)


class FrameClock(Protocol):
    """A protocol for the clock a frame-paced demo advances its waits on."""

    def wait_ms(self, duration_ms: float) -> None:
        """
        A method that holds until the timeline has advanced by a duration.

        :param duration_ms: The duration to advance by.
        """

        ...


class _VirtualClock:
    """
    A clock the page reads in place of the wall clock.

    This class turns on Chrome's virtual time for a target and advances it by one
    interval per frame, so the page's timers, animations, and transitions run on the
    timeline the frames are stamped with. The compositor otherwise measures each
    frame against the real clock, and a render slower than real time sees each
    frame as late and snaps or skips the transitions it was asked to draw.

    The base and the elapsed time are kept per target across clocks, because a
    frame stamped behind one the compositor has already seen is rejected, and a
    second capture of the same page has to carry on from where the first left off.
    """

    _base_ms: ClassVar[dict[str, float]] = {}
    _elapsed_ms: ClassVar[dict[str, float]] = {}

    def __init__(self, session: CDPSession, *, target_id: str) -> None:
        """
        The constructor for the _VirtualClock class.

        :param session: The session attached to the target the clock drives.
        :param target_id: The target the elapsed time is kept against.
        """

        self._expired = asyncio.Event()
        self._session = session
        self._target_id = target_id

        session.on('Emulation.virtualTimeBudgetExpired', self._expire)

    def _expire(self, event: dict[str, object]) -> None:
        """
        A method that marks the granted budget as used up.

        :param event: The event the browser sent, which carries nothing the clock needs.
        """

        _ = event

        self._expired.set()

    @property
    def elapsed_ms(self) -> float:
        """
        A property that reports how far the target's virtual time has advanced.

        :return: The milliseconds advanced since virtual time was turned on.
        """

        return self._elapsed_ms.get(self._target_id, 0.0)

    @property
    def ticks(self) -> float:
        """
        A property that reports the current virtual time as the compositor counts it.

        :return: The timestamp to stamp the next frame with, in renderer ticks.
        :raises RuntimeError: If the virtual time has fallen below zero.
        """

        ticks = self._base_ms.get(self._target_id, 0.0) + self.elapsed_ms

        if ticks < 0:
            message = f'virtual time must not run below zero: {ticks}'
            raise RuntimeError(message)

        return ticks

    async def advanced(self, interval_ms: float) -> None:
        """
        A method that lets the page's time move forward by one interval.

        :param interval_ms: The time the frame covers.
        :raises TimeoutError: If the browser never reports the budget as used up.
        """

        parameters = {
            'policy': 'advance',
            'budget': interval_ms,
            'maxVirtualTimeTaskStarvationCount': VIRTUAL_TIME_STARVATION_COUNT_MAX,
        }

        self._expired.clear()

        await self._session.send('Emulation.setVirtualTimePolicy', parameters)
        await asyncio.wait_for(self._expired.wait(), timeout=FRAME_TIMEOUT_SECONDS)

        self._elapsed_ms[self._target_id] = self.elapsed_ms + interval_ms

    async def paused(self) -> None:
        """
        A method that turns virtual time on, or holds it, and reads where it starts.

        A base that differs from the one seen before means the page moved to a new
        document, which reports the clock from its own start. The elapsed time is
        carried over against the new base so the frame stamps stay continuous,
        because a frame stamped behind one the compositor has already seen is
        never completed. A base beyond the last stamp is a fresh renderer clock,
        and the elapsed time starts over with it.
        """

        result = await self._session.send('Emulation.setVirtualTimePolicy', {'policy': 'pause'})
        base_ms = float(result['virtualTimeTicksBase'])
        ticks_before = self.ticks

        self._base_ms[self._target_id] = base_ms
        self._elapsed_ms[self._target_id] = max(0.0, ticks_before - base_ms)


@dataclass(frozen=True)
class _Attachment:
    """A record of the session and the virtual clock attached to one target."""

    clock: _VirtualClock
    session: CDPSession
    target_id: str


class _NavigationWatch:
    """
    A watch on the frames a page is loading.

    This class tracks the loads in flight so the renderer can hold its capture
    while a document is being replaced, because a frame requested mid-navigation
    comes back blank or times out.
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        """
        The constructor for the _NavigationWatch class.

        :param clock: The clock the settling period is measured on.
        """

        self._clock = clock
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

        return self._clock() < self._settled_at

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
            self._settled_at = self._clock() + NAVIGATION_SETTLE_SECONDS

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
    to the browser. Each frame is produced by asking the compositor for one at a
    timestamp the renderer chooses, so the timeline is the renderer's rather than the
    wall clock's, and a slow screenshot lengthens the recording instead of dropping a
    frame from it.
    """

    registry: ClassVar[dict[int, FrameRenderer]] = {}

    def __init__(
        self,
        page: Page,
        *,
        endpoint: str,
        clock: Callable[[], float] = time.monotonic,
        fps: int = FRAME_FPS_DEFAULT,
        screenshot_format: str = SCREENSHOT_FORMAT_DEFAULT,
        screenshot_quality: int = SCREENSHOT_QUALITY_DEFAULT,
    ) -> None:
        """
        The constructor for the FrameRenderer class.

        :param page: The page the frames are captured from.
        :param endpoint: The URL of the debugging endpoint the capture connects over.
        :param clock: The clock the stall timeout is measured on.
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
                f'screenshot_quality must not exceed {SCREENSHOT_QUALITY_MAX}: {screenshot_quality}'
            )

            raise ValueError(message)

        self._clock = clock
        self._color_scheme: ColorScheme = 'light'
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
        """
        A property that exposes the frame rate the timeline advances at.

        :return: The frames per second.
        """

        return self._fps

    @property
    def frame_count(self) -> int:
        """
        A property that exposes how many frames have been captured.

        :return: The number of frames captured so far.
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

    async def _attached(self, browser: Browser, navigation: _NavigationWatch) -> _Attachment:
        """
        A method that attaches a session and a paused virtual clock to the current target.

        :param browser: The browser the session is opened on.
        :param navigation: The watch subscribed to the page events of the session.
        :return: The attachment for the current target.
        :raises RenderError: If no page carries the target.
        """

        target_id = self._target_id

        session = await _session_attached(
            browser,
            color_scheme=self._color_scheme,
            target_id=target_id,
            endpoint=self._endpoint,
            navigation=navigation,
        )

        clock = _VirtualClock(session, target_id=target_id)

        await clock.paused()

        return _Attachment(clock=clock, session=session, target_id=target_id)

    def _error_raised(self) -> None:
        """
        A method that re-raises whatever killed the capture thread.

        The error is cleared as it is raised, so a failure surfaces once at the first
        call that notices it rather than at each call after.

        :raises RenderError: If the capture thread failed.
        """

        error = self._error

        if error is None:
            return

        self._error = None

        message = 'the frame renderer failed'
        raise RenderError(message) from error

    async def _frame_captured(
        self,
        attachment: _Attachment,
        sink: FrameSink,
        image_last: bytes,
    ) -> bytes:
        """
        A method that captures one frame and writes it to the sink.

        :param attachment: The attachment the frame is captured through.
        :param sink: The destination the frame is written to.
        :param image_last: The image of the previous frame, or empty bytes before the first.
        :return: The image written for this frame, or empty bytes if there is none yet.
        :raises TimeoutError: If the compositor or the virtual clock does not answer in time.
        :raises RenderError: If the sink writes less than the whole frame.
        """

        image = await _frame_rendered(
            attachment.session,
            ticks=attachment.clock.ticks,
            interval_ms=self._interval_ms,
            screenshot=self._screenshot,
        )

        await attachment.clock.advanced(self._interval_ms)

        image_kept = image or image_last

        if image_kept:
            byte_count = sink.write(self._frame_count, image_kept)

            if byte_count != len(image_kept):
                message = (
                    f'frame {self._frame_count} was cut short: '
                    f'{byte_count} of {len(image_kept)} bytes written'
                )

                raise RenderError(message)

        self._frame_count += 1
        self._ready.set()

        return image_kept

    async def _frames_captured(self, browser: Browser, sink: FrameSink) -> CDPSession:
        """
        A method that runs the frame loop on a connected browser.

        The session is reattached when the renderer is switched to a new page, and no
        frame is captured while a navigation is in progress.

        :param browser: The browser the capture is connected to.
        :param sink: The destination the frames are written to.
        :return: The session attached when the renderer was stopped.
        :raises RenderError: If no page carries the target, or a count reaches its maximum.
        """

        navigation = _NavigationWatch()
        attachment = await self._attached(browser, navigation)
        image_last = b''
        navigated = False

        for _ in range(RENDER_STEP_COUNT_MAX):
            if self._stop.is_set():
                return attachment.session

            if self._frame_count >= FRAME_COUNT_MAX:
                message = f'the frame renderer passed {FRAME_COUNT_MAX} frames; aborting'
                raise RenderError(message)

            if self._target_id != attachment.target_id:
                await attachment.session.detach()

                attachment = await self._attached(browser, navigation)

            step_due_at = self._clock() + self._interval_ms / 1000

            if navigation.in_progress:
                navigated = True

                await attachment.clock.advanced(self._interval_ms)
            else:
                if navigated:
                    navigated = False

                    await attachment.clock.paused()

                image_last = await self._frame_captured(attachment, sink, image_last)

            step_rest_seconds = step_due_at - self._clock()

            if step_rest_seconds > 0:
                await asyncio.sleep(step_rest_seconds)

        message = f'the frame renderer passed {RENDER_STEP_COUNT_MAX} steps; aborting'
        raise RenderError(message)

    async def _render(self) -> None:
        """
        A method that captures frames until the renderer is stopped.

        A frame is requested at each timestamp on the timeline and the last image is
        written again whenever the compositor returns nothing, so the recording keeps
        its frame rate through a repaint that produces no new pixels. The page runs on
        virtual time that advances one interval per frame, so its own animations keep
        step with the capture however slow the machine is. A navigation pauses the
        frames but keeps virtual time moving, because a paused page runs no tasks and
        the new document would never finish loading; the timeline is carried across
        the new document rather than restarted, so the two halves of the recording
        stay contiguous.

        :raises RuntimeError: If the renderer has no sink.
        :raises RenderError: If the frame count reaches its maximum.
        """

        sink = self._sink

        if sink is None:
            message = 'the frame renderer has no sink'
            raise RuntimeError(message)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.connect_over_cdp(self._endpoint)
            session = await self._frames_captured(browser, sink)

            await session.detach()
            await browser.close()

    async def _render_outcome(self) -> BaseException | None:
        """
        A method that runs the capture and returns its failure rather than raising it.

        :return: The exception the capture raised, or None if it stopped cleanly.
        """

        outcomes = await asyncio.gather(self._render(), return_exceptions=True)

        return outcomes[0]

    def _run(self) -> None:
        """
        A method that runs the capture loop on its own asyncio loop.

        The ready flag is set on failure as well as on the first frame, because the
        starting thread waits on it and would otherwise block until its timeout for a
        capture that has already died.
        """

        outcome = asyncio.run(self._render_outcome())

        if outcome is not None:
            self._error = outcome
            self._ready.set()

    def start(self, sink: FrameSink) -> None:
        """
        A method that opens the sink and starts the capture thread.

        The call blocks until the first frame is captured, so a demo never records
        against a capture that has not attached yet.

        :param sink: The destination the frames are written to.
        :raises RuntimeError: If the renderer is already running.
        :raises RenderError: If no frame arrives in time.
        """

        if self._thread is not None:
            message = 'the frame renderer is already running'
            raise RuntimeError(message)

        self._color_scheme = _color_scheme_of(self._page)
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
            raise RenderError(message)

        self._error_raised()

    def stop(self) -> None:
        """
        A method that stops the capture thread and closes the sink.

        The sink is closed whether or not the thread came down cleanly, because an
        encoder left with an open pipe never finishes writing its file. The capture
        failure is raised in preference to the sink failure, since a sink that could
        not be closed is usually the consequence of the thread that stopped feeding it.

        :raises RenderError: If the thread does not stop in time, the capture failed,
            or the sink could not be closed.
        """

        thread = self._thread

        if thread is None:
            return

        self._stop.set()
        thread.join(STOP_TIMEOUT_SECONDS)

        self._thread = None

        try:
            sink = self._sink
            self._sink = None

            if sink is not None:
                sink.close()
        finally:
            if thread.is_alive():
                message = f'the frame renderer did not stop within {STOP_TIMEOUT_SECONDS}s'
                raise RenderError(message)

            self._error_raised()

    def switch_page(self, page: Page) -> None:
        """
        A method that points the capture at a different page.

        :param page: The page later frames are captured from.
        """

        self._page = page
        self._target_id = _target_id_of(page)

    def wait_ms(self, duration_ms: float) -> None:
        """
        A method that holds until the capture has advanced by a duration.

        The wait counts frames rather than time, so a demo waiting one second waits for
        the second of footage it asked for however long the machine takes to render it.
        A capture that stops producing frames raises rather than holding forever.

        :param duration_ms: The duration to advance by.
        :raises RenderError: If the capture fails, or renders no frame for the stall timeout.
        """

        if duration_ms <= 0:
            return

        if self._thread is None:
            self._page.wait_for_timeout(duration_ms)

            return

        frame_count_needed = max(1, math.ceil(duration_ms / self._interval_ms))
        frame_count_target = self._frame_count + frame_count_needed
        frame_count_seen = self._frame_count
        slice_count_max = frame_count_needed * WAIT_SLICE_COUNT_PER_FRAME_MAX
        stalled_since = self._clock()

        for _ in range(slice_count_max):
            if self._frame_count >= frame_count_target:
                return

            self._error_raised()

            if self._frame_count != frame_count_seen:
                frame_count_seen = self._frame_count
                stalled_since = self._clock()

            if self._clock() - stalled_since > STALL_SECONDS_MAX:
                message = f'no frame was rendered for {STALL_SECONDS_MAX}s'
                raise RenderError(message)

            self._page.wait_for_timeout(WAIT_SLICE_MS)

        message = f'{frame_count_needed} frames took more than {slice_count_max} waits to render'
        raise RenderError(message)


def renderer_for(page: Page) -> FrameRenderer:
    """
    A function that looks up the renderer registered for a page.

    :param page: The page the renderer captures.
    :return: The renderer registered for the page.
    :raises LookupError: If no renderer is registered for the page.
    """

    renderer = FrameRenderer.registry.get(id(page))

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

    FrameRenderer.registry[id(page)] = renderer


def renderer_unregister(page: Page) -> None:
    """
    A function that drops the renderer registered for a page.

    :param page: The page whose renderer is dropped.
    :raises LookupError: If no renderer is registered for the page.
    """

    renderer = FrameRenderer.registry.pop(id(page), None)

    if renderer is None:
        message = 'no FrameRenderer is registered for the page, so none can be dropped'
        raise LookupError(message)


def _color_scheme_of(page: Page) -> ColorScheme:
    """
    A function that reads the color scheme a page is rendered in.

    :param page: The page to read.
    :return: Dark if the page prefers a dark color scheme, light otherwise.
    """

    dark = page.evaluate(COLOR_SCHEME_DARK_SCRIPT)

    return 'dark' if dark else 'light'


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


async def _session_attached(
    browser: Browser,
    *,
    color_scheme: ColorScheme,
    target_id: str,
    endpoint: str,
    navigation: _NavigationWatch,
) -> CDPSession:
    """
    A function that attaches a session to the page carrying a target.

    The pages are searched rather than addressed directly, because a target opened
    by the demo appears in the connection a moment after the browser reports it, so
    the search is retried until it does. The connection applies its own default
    emulation to each page it attaches to, so the page is given back the color
    scheme the demo opened it with.

    :param browser: The browser the session is opened on.
    :param color_scheme: The color scheme the page was opened with.
    :param target_id: The target the session must reach.
    :param endpoint: The URL of the debugging endpoint, used in the error message.
    :param navigation: The watch subscribed to the page events of the session.
    :return: The session attached to the page.
    :raises RenderError: If no page carries the target.
    """

    for _ in range(TARGET_ATTACH_ATTEMPT_COUNT_MAX):
        for context in browser.contexts:
            for page in context.pages:
                session = await context.new_cdp_session(page)
                target_info = await session.send('Target.getTargetInfo')

                if target_info['targetInfo']['targetId'] == target_id:
                    await page.emulate_media(color_scheme=color_scheme)
                    await navigation.watch(session)

                    return session

                await session.detach()

        await asyncio.sleep(TARGET_ATTACH_RETRY_SECONDS)

    message = f'no page with target {target_id} is reachable at {endpoint}'
    raise RenderError(message)


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
