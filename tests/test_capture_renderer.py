from __future__ import annotations

import asyncio
import base64
import threading

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from typing_extensions import override

from limelight.capture.renderer import (
    WAIT_SLICE_MS,
    FrameRenderer,
    _frame_rendered,
    _NavigationWatch,
    _session_attached,
    _target_id_of,
    _ticks_now,
    _ticks_seeded,
    renderer_for,
    renderer_register,
    renderer_unregister,
)

from fakes import FakePage

if TYPE_CHECKING:
    from typing import Any

    from playwright.sync_api import Page


class TickingPage(FakePage):
    def __init__(self, renderer_holder: list[FrameRenderer]) -> None:
        super().__init__()

        self._renderer_holder = renderer_holder

    @override
    def wait_for_timeout(self, ms: float) -> None:
        super().wait_for_timeout(ms)

        self._renderer_holder[0]._frame_count += 1


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

    with pytest.raises(RuntimeError, match='frame renderer failed'):
        renderer.wait_ms(100)


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


def test_navigation_watch_pauses_until_every_frame_stops_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watch = _NavigationWatch()
    clock = iter([100.0, 100.0, 100.0, 100.2])

    monkeypatch.setattr('limelight.capture.renderer.time.monotonic', lambda: next(clock))

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


def _awaitable(result: object) -> Any:
    async def call(*arguments: object) -> object:
        _ = arguments

        return result

    return call


class FakeCdpSession:
    def __init__(self, results: dict[str, object]) -> None:
        self.detached = False
        self.sends: list[str] = []
        self._results = results

    async def detach(self) -> None:
        self.detached = True

    async def send(self, method: str, parameters: object = None) -> object:
        self.sends.append(method)

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


def test_seeded_ticks_start_at_the_clock_for_an_unseen_target() -> None:
    assert _ticks_seeded({}, 'target', 16.0) > 0


def test_seeded_ticks_follow_a_recent_frame() -> None:
    ticks_last = _ticks_now() + 1000.0

    assert _ticks_seeded({'target': ticks_last}, 'target', 16.0) == ticks_last + 16.0


def test_seeded_ticks_skip_a_stale_frame() -> None:
    ticks = _ticks_seeded({'target': 0.0}, 'target', 16.0)

    assert ticks >= _ticks_now() - 1000


def test_the_target_id_comes_from_the_page_session() -> None:
    session = SyncCdpSession('target-7')
    context = SimpleNamespace(new_cdp_session=lambda page: session)
    page = SimpleNamespace(context=context)

    assert _target_id_of(cast('Any', page)) == 'target-7'
    assert session.detached is True


def test_an_unreachable_target_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.capture.renderer.TARGET_ATTACH_ATTEMPT_COUNT_MAX', 2)
    monkeypatch.setattr('limelight.capture.renderer.TARGET_ATTACH_RETRY_SECONDS', 0)

    browser = SimpleNamespace(contexts=[])
    navigation = _NavigationWatch()

    with pytest.raises(RuntimeError, match='no page with target absent is reachable'):
        asyncio.run(
            _session_attached(
                cast('Any', browser),
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

    with pytest.raises(RuntimeError, match='no page with target wanted is reachable'):
        asyncio.run(
            _session_attached(
                cast('Any', browser),
                target_id='wanted',
                endpoint='ws://localhost:1',
                navigation=_NavigationWatch(),
            ),
        )

    assert session.detached is True
