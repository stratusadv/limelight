from __future__ import annotations

import asyncio
import base64
import threading

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from typing_extensions import override

from limelight import RenderError
from limelight.capture import renderer
from limelight.capture.renderer import (
    STALL_SECONDS_MAX,
    WAIT_SLICE_MS,
    FrameRenderer,
    _Attachment,
    _frame_rendered,
    _NavigationWatch,
    _session_attached,
    _target_id_of,
    _VirtualClock,
    renderer_for,
    renderer_register,
    renderer_unregister,
)

from fakes import FakePage

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any

    from playwright.sync_api import Page


CAPTURE_FRAME_COUNT = 5
CLOCK_READING_COUNT_MAX = 100
NAVIGATION_STEP_COUNT = 4
STALLED_WAIT_COUNT_MAX = 10


class StalledPage(FakePage):
    @override
    def wait_for_timeout(self, timeout: float) -> None:
        super().wait_for_timeout(timeout)

        if len(self.waits_ms) > STALLED_WAIT_COUNT_MAX:
            pytest.fail('the wait held on through a capture that rendered nothing')


class TickingPage(FakePage):
    def __init__(self, renderer_holder: list[FrameRenderer]) -> None:
        super().__init__()

        self._renderer_holder = renderer_holder

    @override
    def wait_for_timeout(self, timeout: float) -> None:
        super().wait_for_timeout(timeout)

        self._renderer_holder[0]._frame_count += 1


def asyncio_sleeping(sleep: Callable[[float], Awaitable[None]]) -> SimpleNamespace:
    functions = {**vars(asyncio), 'sleep': sleep}

    return SimpleNamespace(**functions)


def clock_stepping(step_seconds: float) -> Callable[[], float]:
    instants = (index * step_seconds for index in range(CLOCK_READING_COUNT_MAX))

    def instant_next() -> float:
        return next(instants)

    return instant_next


def renderer_build(page: FakePage | None = None) -> FrameRenderer:
    page = page if page is not None else FakePage()

    return FrameRenderer(cast('Page', page), endpoint='http://127.0.0.1:9333')


def test_fps_must_be_in_range() -> None:
    with pytest.raises(ValueError, match='fps'):
        FrameRenderer(FakePage().as_page(), endpoint='http://127.0.0.1:9333', fps=0)


def test_screenshot_format_must_be_known() -> None:
    with pytest.raises(ValueError, match='screenshot_format'):
        FrameRenderer(
            FakePage().as_page(),
            endpoint='http://127.0.0.1:9333',
            screenshot_format='bmp',
        )


def test_screenshot_quality_must_be_in_range() -> None:
    with pytest.raises(ValueError, match='screenshot_quality'):
        FrameRenderer(
            FakePage().as_page(),
            endpoint='http://127.0.0.1:9333',
            screenshot_quality=101,
        )


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

    with pytest.raises(RenderError, match='frame renderer failed'):
        renderer.wait_ms(100)


def test_wait_ms_raises_when_no_frame_arrives_within_the_stall_bound() -> None:
    page = StalledPage()
    clock = clock_stepping(STALL_SECONDS_MAX / 2)
    renderer = FrameRenderer(page.as_page(), endpoint='http://127.0.0.1:9333', clock=clock)
    renderer._thread = threading.Thread(target=lambda: None)

    with pytest.raises(RenderError, match='no frame was rendered'):
        renderer.wait_ms(100)

    assert page.waits_ms == [WAIT_SLICE_MS] * 2


def test_wait_ms_measures_the_stall_from_the_latest_frame() -> None:
    holder: list[FrameRenderer] = []
    page = TickingPage(holder)
    clock = clock_stepping(STALL_SECONDS_MAX)
    renderer = FrameRenderer(page.as_page(), endpoint='http://127.0.0.1:9333', clock=clock)

    holder.append(renderer)
    renderer._thread = threading.Thread(target=lambda: None)

    renderer.wait_ms(100)

    assert renderer.frame_count == 6


def test_stop_without_start_is_a_no_op() -> None:
    renderer = renderer_build()

    renderer.stop()

    assert renderer.is_running is False


def test_registry_maps_a_page_to_its_renderer() -> None:
    page = FakePage().as_page()
    renderer = renderer_build()

    with pytest.raises(LookupError, match='FrameRenderer'):
        renderer_for(page)

    renderer_register(page, renderer)

    assert renderer_for(page) is renderer

    renderer_unregister(page)

    with pytest.raises(LookupError, match='FrameRenderer'):
        renderer_for(page)


def test_unregister_rejects_a_page_with_no_renderer() -> None:
    page = FakePage().as_page()

    with pytest.raises(LookupError, match='none can be dropped'):
        renderer_unregister(page)


def test_navigation_watch_pauses_until_every_frame_stops_loading() -> None:
    clock = iter([100.0, 100.0, 100.0, 100.2])
    watch = _NavigationWatch(clock=lambda: next(clock))

    assert watch.in_progress is False

    watch._started({'frameId': 'main'})
    watch._started({'frameId': 'child'})

    assert watch.in_progress is True

    watch._stopped({'frameId': 'child'})

    assert watch.in_progress is True

    watch._stopped({'frameId': 'main'})

    assert watch.in_progress is True
    assert watch.in_progress is False


def test_a_non_positive_fps_is_refused() -> None:
    with pytest.raises(ValueError, match='fps must be positive: 0'):
        FrameRenderer(cast('Page', FakePage()), endpoint='http://127.0.0.1:9333', fps=0)


def test_an_fps_beyond_the_ceiling_is_refused() -> None:
    with pytest.raises(ValueError, match='fps must not exceed'):
        FrameRenderer(cast('Page', FakePage()), endpoint='http://127.0.0.1:9333', fps=100000)


def test_an_unknown_screenshot_format_is_refused() -> None:
    with pytest.raises(ValueError, match='screenshot_format must be one of'):
        FrameRenderer(
            cast('Page', FakePage()),
            endpoint='http://127.0.0.1:9333',
            screenshot_format='gif',
        )


def test_a_negative_screenshot_quality_is_refused() -> None:
    with pytest.raises(ValueError, match='screenshot_quality must be non-negative'):
        FrameRenderer(
            cast('Page', FakePage()),
            endpoint='http://127.0.0.1:9333',
            screenshot_quality=-1,
        )


def test_a_screenshot_quality_beyond_the_ceiling_is_refused() -> None:
    with pytest.raises(ValueError, match='screenshot_quality must not exceed'):
        FrameRenderer(
            cast('Page', FakePage()),
            endpoint='http://127.0.0.1:9333',
            screenshot_quality=101,
        )


def test_a_png_capture_carries_no_quality() -> None:
    renderer = FrameRenderer(
        cast('Page', FakePage()),
        endpoint='http://127.0.0.1:9333',
        screenshot_format='png',
    )

    assert renderer._screenshot == {'format': 'png'}


def test_a_jpeg_capture_carries_its_quality() -> None:
    renderer = FrameRenderer(
        cast('Page', FakePage()),
        endpoint='http://127.0.0.1:9333',
        screenshot_quality=80,
    )

    assert renderer._screenshot == {'format': 'jpeg', 'quality': 80}


def _awaitable(result: object) -> Callable[..., Awaitable[object]]:
    async def call(*arguments: object) -> object:
        _ = arguments

        await asyncio.sleep(0)

        return result

    return call


class FakeCdpSession:
    def __init__(self, results: dict[str, object], *, budget_expires: bool = True) -> None:
        self.detached = False
        self.handlers: dict[str, Callable[[dict[str, object]], None]] = {}
        self.parameters: list[object] = []
        self.sends: list[str] = []
        self._budget_expires = budget_expires
        self._results = results

    async def detach(self) -> None:
        self.detached = True

    def on(self, event: str, handler: Callable[[dict[str, object]], None]) -> None:
        self.handlers[event] = handler

    async def send(self, method: str, parameters: object = None) -> object:
        self.sends.append(method)
        self.parameters.append(parameters)

        if method == 'Emulation.setVirtualTimePolicy':
            policy = cast('dict[str, object]', parameters)['policy']

            if policy == 'advance':
                if self._budget_expires:
                    self.handlers['Emulation.virtualTimeBudgetExpired']({})

            return {'virtualTimeTicksBase': self._results.get('base', 5000.0)}

        return self._results.get(method, {})


class SyncCdpSession:
    def __init__(self, target_id: str) -> None:
        self.detached = False
        self._target_id = target_id

    def detach(self) -> None:
        self.detached = True

    def send(self, method: str, parameters: object = None) -> object:
        _ = method
        _ = parameters

        return {'targetInfo': {'targetId': self._target_id}}


def test_a_frame_without_image_data_reads_as_empty() -> None:
    session = FakeCdpSession({})

    image = asyncio.run(
        _frame_rendered(
            cast('Any', session),
            ticks=1.0,
            interval_ms=16.0,
            screenshot={'format': 'jpeg', 'quality': 100},
        ),
    )

    assert image == b''
    assert session.sends == ['HeadlessExperimental.beginFrame']


def test_a_frame_carries_its_decoded_image() -> None:
    encoded = base64.b64encode(b'frame').decode()
    session = FakeCdpSession({'HeadlessExperimental.beginFrame': {'screenshotData': encoded}})

    image = asyncio.run(
        _frame_rendered(
            cast('Any', session),
            ticks=1.0,
            interval_ms=16.0,
            screenshot={'format': 'png'},
        ),
    )

    assert image == b'frame'


def test_virtual_clock_starts_at_the_base_the_browser_reports() -> None:
    session = FakeCdpSession({'base': 7000.0})
    clock = _VirtualClock(cast('Any', session), target_id='clock-base')

    asyncio.run(clock.paused())

    assert clock.ticks == pytest.approx(7000.0)
    assert session.parameters == [{'policy': 'pause'}]


def test_virtual_clock_advances_one_interval_per_frame() -> None:
    session = FakeCdpSession({'base': 7000.0})
    clock = _VirtualClock(cast('Any', session), target_id='clock-advance')

    async def frames() -> None:
        await clock.paused()
        await clock.advanced(16.0)
        await clock.advanced(16.0)

    asyncio.run(frames())

    advance = cast('dict[str, object]', session.parameters[1])

    assert clock.ticks == pytest.approx(7032.0)
    assert advance['policy'] == 'advance'
    assert advance['budget'] == pytest.approx(16.0)


def test_virtual_clock_carries_elapsed_time_to_a_later_clock_on_the_same_target() -> None:
    session = FakeCdpSession({'base': 7000.0})
    clock = _VirtualClock(cast('Any', session), target_id='clock-carry')

    async def frames() -> None:
        await clock.paused()
        await clock.advanced(16.0)

    asyncio.run(frames())

    session_next = FakeCdpSession({'base': 7000.0})
    clock_next = _VirtualClock(cast('Any', session_next), target_id='clock-carry')

    asyncio.run(clock_next.paused())

    assert clock_next.ticks == pytest.approx(7016.0)


def test_virtual_clock_starts_over_when_the_base_changes() -> None:
    session = FakeCdpSession({'base': 7000.0})
    clock = _VirtualClock(cast('Any', session), target_id='clock-reset')

    async def frames() -> None:
        await clock.paused()
        await clock.advanced(16.0)

    asyncio.run(frames())

    session_next = FakeCdpSession({'base': 9000.0})
    clock_next = _VirtualClock(cast('Any', session_next), target_id='clock-reset')

    asyncio.run(clock_next.paused())

    assert clock_next.ticks == pytest.approx(9000.0)


def test_virtual_clock_keeps_its_stamps_continuous_when_a_new_document_moves_the_base() -> None:
    session = FakeCdpSession({'base': 7000.0})
    clock = _VirtualClock(cast('Any', session), target_id='clock-document')

    async def frames() -> None:
        await clock.paused()

        for _ in range(5):
            await clock.advanced(16.0)

    asyncio.run(frames())

    session_next = FakeCdpSession({'base': 7020.0})
    clock_next = _VirtualClock(cast('Any', session_next), target_id='clock-document')

    asyncio.run(clock_next.paused())

    assert clock_next.ticks == pytest.approx(7080.0)
    assert clock_next.elapsed_ms == pytest.approx(60.0)


def test_virtual_clock_raises_when_the_budget_never_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(renderer, 'FRAME_TIMEOUT_SECONDS', 0.01)

    session = FakeCdpSession({}, budget_expires=False)
    clock = _VirtualClock(cast('Any', session), target_id='clock-stall')

    with pytest.raises(TimeoutError):
        asyncio.run(clock.advanced(16.0))


def capture_build(
    monkeypatch: pytest.MonkeyPatch,
    target_id: str,
) -> tuple[FrameRenderer, list[FakeCdpSession], list[bytes]]:
    capture = renderer_build()
    sessions: list[FakeCdpSession] = []
    images_last: list[bytes] = []

    async def attached(*_: object) -> _Attachment:
        await asyncio.sleep(0)

        session = FakeCdpSession({})
        clock = _VirtualClock(cast('Any', session), target_id=capture._target_id)

        sessions.append(session)

        return _Attachment(
            clock=clock,
            session=cast('Any', session),
            target_id=capture._target_id,
        )

    async def frame_captured(_: object, __: object, image_last: bytes) -> bytes:
        await asyncio.sleep(0)

        images_last.append(image_last)

        return image_last + b'x'

    capture._target_id = target_id

    monkeypatch.setattr(capture, '_attached', attached)
    monkeypatch.setattr(capture, '_frame_captured', frame_captured)

    return capture, sessions, images_last


def frames_capture(capture: FrameRenderer) -> object:
    return asyncio.run(capture._frames_captured(cast('Any', object()), cast('Any', object())))


def test_a_capture_that_dies_wakes_the_starter_with_its_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = renderer_build()

    async def render_failing() -> None:
        await asyncio.sleep(0)

        message = 'boom'
        raise RuntimeError(message)

    monkeypatch.setattr(capture, '_render', render_failing)

    capture._run()

    assert capture._ready.is_set()
    assert str(capture._error) == 'boom'


def test_a_capture_cancelled_out_from_under_it_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = renderer_build()

    async def render_cancelled() -> None:
        await asyncio.sleep(0)

        raise asyncio.CancelledError

    monkeypatch.setattr(capture, '_render', render_cancelled)

    capture._run()

    assert capture._ready.is_set()
    assert isinstance(capture._error, asyncio.CancelledError)


def test_a_capture_that_ends_cleanly_reports_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = renderer_build()

    async def render_clean() -> None:
        await asyncio.sleep(0)

    monkeypatch.setattr(capture, '_render', render_clean)

    capture._run()

    assert capture._ready.is_set() is False
    assert capture._error is None


def test_a_capture_stops_at_its_step_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    capture, _, images_last = capture_build(monkeypatch, 'target-bound')

    monkeypatch.setattr('limelight.capture.renderer.RENDER_STEP_COUNT_MAX', 3)

    with pytest.raises(RenderError, match='passed 3 steps'):
        frames_capture(capture)

    assert images_last == [b'', b'x', b'xx']


def test_a_capture_stops_at_its_frame_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    capture, _, _ = capture_build(monkeypatch, 'target-frames')

    monkeypatch.setattr('limelight.capture.renderer.FRAME_COUNT_MAX', 0)

    with pytest.raises(RenderError, match='passed 0 frames'):
        frames_capture(capture)


def test_a_stopped_capture_hands_back_the_session_it_holds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture, sessions, images_last = capture_build(monkeypatch, 'target-stop')

    capture._stop.set()

    session = frames_capture(capture)

    assert session is sessions[0]
    assert images_last == []


def test_a_switched_target_moves_the_capture_and_keeps_its_last_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture, sessions, images_last = capture_build(monkeypatch, 'target-first')
    frame_captured = capture._frame_captured

    async def frame_switching(attachment: object, sink: object, image_last: bytes) -> bytes:
        image = await frame_captured(cast('Any', attachment), cast('Any', sink), image_last)

        if len(images_last) == 1:
            capture._target_id = 'target-second'
        else:
            capture._stop.set()

        return image

    monkeypatch.setattr(capture, '_frame_captured', frame_switching)

    session = frames_capture(capture)

    assert len(sessions) == 2
    assert sessions[0].detached is True
    assert sessions[1].detached is False
    assert session is sessions[1]
    assert images_last == [b'', b'x']


def test_a_navigation_holds_the_frames_until_it_settles(monkeypatch: pytest.MonkeyPatch) -> None:
    capture, sessions, images_last = capture_build(monkeypatch, 'target-navigation')
    moments = iter([0.0, 0.0, 1.0, 1.0, 1.0])

    def clock() -> float:
        return next(moments)

    watch = _NavigationWatch(clock=clock)

    watch._started({'frameId': 'main'})
    watch._stopped({'frameId': 'main'})

    monkeypatch.setattr('limelight.capture.renderer._NavigationWatch', lambda: watch)
    monkeypatch.setattr('limelight.capture.renderer.RENDER_STEP_COUNT_MAX', 3)

    with pytest.raises(RenderError, match='passed 3 steps'):
        frames_capture(capture)

    policies = [parameters for parameters in sessions[0].parameters if isinstance(parameters, dict)]

    assert policies[0]['policy'] == 'advance'
    assert policies[1]['policy'] == 'pause'
    assert images_last == [b'', b'x']


def test_a_navigation_moves_the_page_clock_no_faster_than_the_wall_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture, sessions, _ = capture_build(monkeypatch, 'target-paced')
    wall = SimpleNamespace(seconds=0.0)

    async def sleep_simulated(seconds: float) -> None:
        wall.seconds += seconds

        await asyncio.sleep(0)

    watch = _NavigationWatch()

    watch._started({'frameId': 'main'})

    monkeypatch.setattr(capture, '_clock', lambda: wall.seconds)
    monkeypatch.setattr(renderer, 'asyncio', asyncio_sleeping(sleep_simulated))
    monkeypatch.setattr('limelight.capture.renderer._NavigationWatch', lambda: watch)
    monkeypatch.setattr('limelight.capture.renderer.RENDER_STEP_COUNT_MAX', NAVIGATION_STEP_COUNT)

    with pytest.raises(RenderError, match=f'passed {NAVIGATION_STEP_COUNT} steps'):
        frames_capture(capture)

    policies = [parameters for parameters in sessions[0].parameters if isinstance(parameters, dict)]
    advance_count = sum(1 for policy in policies if policy['policy'] == 'advance')
    page_ms = advance_count * capture._interval_ms

    assert advance_count == NAVIGATION_STEP_COUNT
    assert wall.seconds * 1000 == pytest.approx(page_ms)


def test_a_capture_slower_than_the_wall_clock_is_never_held_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture, _, images_last = capture_build(monkeypatch, 'target-slow')
    frame_captured = capture._frame_captured
    sleeps: list[float] = []

    async def sleep_recorded(seconds: float) -> None:
        sleeps.append(seconds)

        await asyncio.sleep(0)

    async def frame_counted(attachment: object, sink: object, image_last: bytes) -> bytes:
        image = await frame_captured(cast('Any', attachment), cast('Any', sink), image_last)

        if len(images_last) == CAPTURE_FRAME_COUNT:
            capture._stop.set()

        return image

    monkeypatch.setattr(capture, '_clock', clock_stepping(1.0))
    monkeypatch.setattr(capture, '_frame_captured', frame_counted)
    monkeypatch.setattr(renderer, 'asyncio', asyncio_sleeping(sleep_recorded))

    frames_capture(capture)

    assert len(images_last) == CAPTURE_FRAME_COUNT
    assert [seconds for seconds in sleeps if seconds > 0] == []


class RecordingSink:
    def __init__(self, *, byte_count_lost: int = 0) -> None:
        self.frames: list[tuple[int, bytes]] = []
        self._byte_count_lost = byte_count_lost

    def close(self) -> None:
        _ = self

    def open(self) -> None:
        _ = self

    def write(self, index: int, image: bytes) -> int:
        frame = (index, image)
        self.frames.append(frame)

        return len(image) - self._byte_count_lost


def attachment_rendering(image: bytes, *, target_id: str) -> _Attachment:
    encoded = base64.b64encode(image).decode()
    session = FakeCdpSession({'HeadlessExperimental.beginFrame': {'screenshotData': encoded}})
    clock = _VirtualClock(cast('Any', session), target_id=target_id)

    return _Attachment(clock=clock, session=cast('Any', session), target_id=target_id)


def test_a_frame_written_in_full_advances_the_count() -> None:
    capture = renderer_build()
    attachment = attachment_rendering(b'frame', target_id='sink-full')
    sink = RecordingSink()

    image = asyncio.run(capture._frame_captured(attachment, sink, b''))

    assert image == b'frame'
    assert sink.frames == [(0, b'frame')]
    assert capture.frame_count == 1


def test_a_frame_the_sink_cuts_short_is_reported() -> None:
    capture = renderer_build()
    attachment = attachment_rendering(b'frame', target_id='sink-short')
    sink = RecordingSink(byte_count_lost=1)

    with pytest.raises(RenderError, match='frame 0 was cut short: 4 of 5 bytes written'):
        asyncio.run(capture._frame_captured(attachment, sink, b''))

    assert capture.frame_count == 0


def test_the_target_id_comes_from_the_page_session() -> None:
    session = SyncCdpSession('target-7')
    context = SimpleNamespace(new_cdp_session=lambda _: session)
    page = SimpleNamespace(context=context)

    assert _target_id_of(cast('Any', page)) == 'target-7'
    assert session.detached is True


def test_an_unreachable_target_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.capture.renderer.TARGET_ATTACH_ATTEMPT_COUNT_MAX', 2)
    monkeypatch.setattr('limelight.capture.renderer.TARGET_ATTACH_RETRY_SECONDS', 0)

    browser = SimpleNamespace(contexts=[])
    navigation = _NavigationWatch()

    with pytest.raises(RenderError, match='no page with target absent is reachable'):
        asyncio.run(
            _session_attached(
                cast('Any', browser),
                color_scheme='light',
                target_id='absent',
                endpoint='ws://localhost:1',
                navigation=navigation,
            ),
        )


def test_a_session_for_another_target_is_detached() -> None:
    session = FakeCdpSession({'Target.getTargetInfo': {'targetInfo': {'targetId': 'other'}}})
    context = SimpleNamespace(new_cdp_session=_awaitable(session))
    browser = SimpleNamespace(contexts=[SimpleNamespace(pages=['page'])])

    browser.contexts[0].new_cdp_session = context.new_cdp_session

    with pytest.raises(RenderError, match='no page with target wanted is reachable'):
        asyncio.run(
            _session_attached(
                cast('Any', browser),
                color_scheme='light',
                target_id='wanted',
                endpoint='ws://localhost:1',
                navigation=_NavigationWatch(),
            ),
        )

    assert session.detached is True
