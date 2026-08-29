from __future__ import annotations

import json

import pytest

from pathlib import Path
from typing import TYPE_CHECKING, cast

from limelight.capture.renderer import renderer_register, renderer_unregister
from limelight.config import VIDEO_QUALITIES, DemoConfig
from limelight.demo import Demo
from limelight.narrator import Silent
from limelight.overlay import Overlay

from fakes import FakeApplication, FakeFrameRenderer, FakeLocator, FakeNarrator, FakePage

if TYPE_CHECKING:
    from limelight.capture.renderer import FrameRenderer
    from limelight.ledger import LedgerRow


NARRATED = DemoConfig(mode='narrate')


@pytest.fixture
def demos_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr('limelight.demo.DIRECTORY_ROOT', str(tmp_path))

    return tmp_path


def demo_build(
    page: FakePage | None = None,
    *,
    config: DemoConfig = NARRATED,
    narrator: FakeNarrator | None = None,
) -> tuple[Demo, FakePage, FakeApplication, FakeNarrator]:
    page = page if page is not None else FakePage()
    application = FakeApplication()
    narrator = narrator if narrator is not None else FakeNarrator()

    demo = Demo(
        page.as_page(),
        application,
        name='demo',
        config=config,
        narrator=narrator.as_narrator(),
    )

    return demo, page, application, narrator


def demo_build_silent(page: FakePage | None = None) -> Demo:
    page = page if page is not None else FakePage()

    return Demo(page.as_page(), FakeApplication(), name='demo', config=DemoConfig())


def test_init_disables_window_print() -> None:
    _, page, _, _ = demo_build()

    assert page.init_scripts == ['window.print = () => {};']


def test_name_required() -> None:
    with pytest.raises(ValueError, match='name'):
        Demo(FakePage().as_page(), FakeApplication(), name='', config=DemoConfig())


def test_directory_sits_under_the_demos_root() -> None:
    demo = demo_build_silent()

    assert demo.directory.parts == ('.demos', 'demo')


def test_goto_logs_in_then_navigates() -> None:
    user = object()
    page = FakePage()
    application = FakeApplication()
    demo = Demo(page.as_page(), application, name='demo', config=DemoConfig(), user=user)

    demo.goto('home:dashboard')

    assert application.logins == [(page, user)]
    assert application.url_requests == [('home:dashboard', {})]
    assert page.goto_urls == ['http://stage.test/home:dashboard']


def test_goto_forwards_url_kwargs() -> None:
    demo, _, application, _ = demo_build()

    demo.goto('order:detail', pk=7)

    assert application.url_requests == [('order:detail', {'pk': 7})]


def test_cards_delegate_to_the_narrator(demos_root: Path) -> None:
    demo, _, _, narrator = demo_build()

    rows: list[LedgerRow] = []

    demo.title('Chapter')
    demo.narrate('Welcome', body='Hello.')
    demo.metrics('Totals', rows)
    demo.spotlight(FakeLocator().as_locator())
    demo.pause()

    call_names = [call[0] for call in narrator.calls]

    assert call_names == ['title', 'narrate', 'metrics', 'spotlight', 'pause']


def test_pause_forwards_its_length() -> None:
    demo, _, _, narrator = demo_build()

    demo.pause(300)

    assert narrator.calls == [('pause', 300)]


def test_actions_delegate_to_the_narrator(demos_root: Path) -> None:
    demo, _, _, narrator = demo_build()
    locator = FakeLocator()
    thumb = FakeLocator()

    demo.click(locator.as_locator())
    demo.fill(locator.as_locator(), 'hello')
    demo.select(locator.as_locator(), 'Approved')
    demo.check(locator.as_locator())
    demo.hover(locator.as_locator())
    demo.press(locator.as_locator(), 'Enter')
    demo.slide(track=locator.as_locator(), thumb=thumb.as_locator())
    demo.uncheck(locator.as_locator())

    call_names = [call[0] for call in narrator.calls]

    assert call_names == [
        'click',
        'fill',
        'select',
        'check',
        'hover',
        'press',
        'slide',
        'uncheck',
    ]

    assert locator.click_count == 0


def test_screenshot_records_the_file_the_narrator_wrote(demos_root: Path) -> None:
    narrator = FakeNarrator(screenshot_path=Path('01-welcome.png'))
    demo, _, _, _ = demo_build(narrator=narrator)

    demo.screenshot('welcome')

    transcript_path = demos_root / 'demo' / 'transcript.json'
    payload = json.loads(transcript_path.read_text(encoding='utf-8'))

    assert narrator.calls == [('screenshot', 'welcome')]
    assert payload['events'][0]['file'] == '01-welcome.png'


def test_screenshot_without_a_file_records_nothing(demos_root: Path) -> None:
    demo, _, _, narrator = demo_build()

    demo.screenshot('welcome')

    assert narrator.calls == [('screenshot', 'welcome')]
    assert not (demos_root / 'demo' / 'transcript.json').exists()


def test_silent_demo_acts_directly_on_the_locator() -> None:
    demo = demo_build_silent()
    locator = FakeLocator()

    demo.click(locator.as_locator())
    demo.fill(locator.as_locator(), 'hello')
    demo.select(locator.as_locator(), 'Approved')
    demo.check(locator.as_locator())
    demo.hover(locator.as_locator())
    demo.press(locator.as_locator(), 'Enter')
    demo.uncheck(locator.as_locator())

    assert locator.click_count == 1
    assert locator.fill_values == ['hello']
    assert locator.select_labels == ['Approved']
    assert locator.check_count == 1
    assert locator.hover_count == 1
    assert locator.pressed_keys == ['Enter']
    assert locator.uncheck_count == 1
    assert locator.typed_sequences == []


def test_silent_demo_slides_via_gesture(monkeypatch: pytest.MonkeyPatch) -> None:
    slides: list[tuple[object, object, object]] = []

    def slide_stub(page: object, *, track: object, thumb: object) -> None:
        slide = (page, track, thumb)
        slides.append(slide)

    monkeypatch.setattr('limelight.narrator.slide_to_end', slide_stub)

    page = FakePage()
    demo = demo_build_silent(page)
    track = FakeLocator()
    thumb = FakeLocator()

    demo.slide(track=track.as_locator(), thumb=thumb.as_locator())

    assert slides == [(page, track, thumb)]


def test_silent_demo_never_touches_the_page() -> None:
    page = FakePage()
    demo = demo_build_silent(page)

    rows: list[LedgerRow] = []

    demo.metrics('Totals', rows)
    demo.narrate('Welcome')
    demo.pause()
    demo.screenshot('welcome')
    demo.spotlight(FakeLocator().as_locator())
    demo.title('Chapter')

    assert page.evaluations == []
    assert page.screenshot_paths == []
    assert page.waits_ms == []


def test_login_as_switches_user_and_logs_in() -> None:
    demo, page, application, _ = demo_build()
    user = object()

    demo.login_as(user)

    assert demo.user is user
    assert application.logins == [(page, user)]


def test_switch_page_switches_page_everywhere() -> None:
    demo, _, _, narrator = demo_build()
    page_second = FakePage()

    demo.switch_page(page_second.as_page())

    assert demo.page is page_second
    assert narrator.calls == [('switch_page', page_second)]
    assert page_second.init_scripts == ['window.print = () => {};']


def test_silent_config_builds_a_silent_narrator() -> None:
    demo = demo_build_silent()

    assert isinstance(demo._narrator, Silent)
    assert demo._transcript is None


def test_narrated_config_builds_the_overlay() -> None:
    page = FakePage()
    demo = Demo(page.as_page(), FakeApplication(), name='demo', config=NARRATED)

    assert isinstance(demo._narrator, Overlay)
    assert '"controls": true' in page.init_scripts[1]


def test_present_config_installs_step_mode() -> None:
    page = FakePage()
    config = DemoConfig(mode='present')

    Demo(page.as_page(), FakeApplication(), name='demo', config=config)

    assert '"stepMode": true' in page.init_scripts[1]


def test_video_config_needs_a_renderer() -> None:
    config = DemoConfig(mode='narrate', video=True)

    with pytest.raises(LookupError, match='FrameRenderer'):
        Demo(FakePage().as_page(), FakeApplication(), name='demo', config=config)


def test_video_config_starts_the_registered_renderer_into_the_directory(demos_root: Path) -> None:
    page = FakePage()
    page_next = FakePage()
    renderer = FakeFrameRenderer()
    config = DemoConfig(mode='narrate', video=True)

    renderer_register(page.as_page(), cast('FrameRenderer', renderer))

    try:
        demo = Demo(page.as_page(), FakeApplication(), name='demo', config=config)
    finally:
        renderer_unregister(page.as_page())

    demo.pause(300)
    demo.switch_page(page_next.as_page())

    assert '"controls": false' in page.init_scripts[1]
    assert len(renderer.sinks) == 1
    assert renderer.sinks[0]._destination == demos_root / 'demo' / 'video.mp4'
    assert renderer.waits_ms == [300]
    assert renderer.page_switches == [page_next.as_page()]
    assert page.waits_ms == []


def test_narrated_demo_records_actions(demos_root: Path) -> None:
    demo, _, _, _ = demo_build()

    locator = FakeLocator()
    locator.label = 'Approve'

    demo.click(locator.as_locator())
    demo.fill(locator.as_locator(), 'SO-100')
    demo.select(locator.as_locator(), 'Approved')
    demo.press(locator.as_locator(), 'Enter')

    transcript_path = demos_root / 'demo' / 'transcript.json'
    payload = json.loads(transcript_path.read_text(encoding='utf-8'))
    events = payload['events']

    assert [event['event'] for event in events] == ['click', 'fill', 'select', 'press']
    assert events[0]['target'] == 'Approve'
    assert events[1]['value'] == 'SO-100'
    assert events[2]['option'] == 'Approved'
    assert events[3]['key'] == 'Enter'


def test_narrated_demo_records_cards(demos_root: Path) -> None:
    demo, _, _, _ = demo_build()

    demo.title('Order Approval')
    demo.narrate('Open the order', body='Navigate to it.')
    demo.spotlight(FakeLocator().as_locator(), label='Here')
    demo.spotlight(FakeLocator().as_locator())

    transcript_path = demos_root / 'demo' / 'transcript.json'
    payload = json.loads(transcript_path.read_text(encoding='utf-8'))
    events = payload['events']

    assert [event['event'] for event in events] == ['title', 'narrate', 'spotlight']
    assert events[1]['title'] == 'Open the order'
    assert events[2]['label'] == 'Here'


def test_shots_config_gives_the_overlay_a_camera(demos_root: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode='narrate', shots=True)
    demo = Demo(page.as_page(), FakeApplication(), name='demo', config=config)

    demo.screenshot('welcome')

    transcript_path = demos_root / 'demo' / 'transcript.json'
    payload = json.loads(transcript_path.read_text(encoding='utf-8'))

    assert page.screenshot_paths == [str(demos_root / 'demo' / '01-welcome.png')]
    assert payload['events'][0]['file'] == '01-welcome.png'


def test_silent_demo_records_no_locator_label() -> None:
    demo = demo_build_silent()
    locator = FakeLocator()
    locator.label = 'Approve'

    demo.click(locator.as_locator())

    assert demo._transcript is None


def test_wait_until_holds_through_the_narrator() -> None:
    demo, _, _, narrator = demo_build()
    outcomes = [False, True]

    demo.wait_until(lambda: outcomes.pop(0), interval_ms=100)

    assert narrator.calls == [('wait', 100)]


def test_wait_holds_through_the_narrator() -> None:
    demo, _, _, narrator = demo_build()

    demo.wait(250)

    assert narrator.calls == [('wait', 250)]


def test_goto_settles_the_page_before_the_login() -> None:
    demo, page, application, _ = demo_build()

    demo.goto('home:dashboard')

    assert page.load_states == ['networkidle']
    assert len(application.logins) == 1


def test_login_as_settles_the_page_before_the_login() -> None:
    demo, page, application, _ = demo_build()

    demo.login_as('other-user')

    assert page.load_states == ['networkidle']
    assert application.logins == [(page.as_page(), 'other-user')]
    assert demo.user == 'other-user'


def test_silent_narrator_switches_pages_and_waits() -> None:
    page_first = FakePage()
    page_second = FakePage()
    narrator = Silent(page_first.as_page())

    narrator.wait(250)
    narrator.switch_page(page_second.as_page())
    narrator.wait(100)

    assert page_first.waits_ms == [250]
    assert page_second.waits_ms == [100]


def test_config_comes_from_the_environment_when_none_is_given(
    monkeypatch: pytest.MonkeyPatch,
    demos_root: Path,
) -> None:
    monkeypatch.setenv('DEMO_MODE', 'silent')
    monkeypatch.setenv('DEMO_STEP_MS', '1234')

    demo = Demo(FakePage().as_page(), FakeApplication(), name='demo')

    assert demo.config.step_ms == 1234
    assert isinstance(demo._narrator, Silent)


def test_a_hold_of_no_length_is_refused() -> None:
    demo, _, _, _ = demo_build()
    locator = FakeLocator()

    with pytest.raises(ValueError, match='ms must be positive: 0'):
        demo.wait(0)

    with pytest.raises(ValueError, match='ms must be positive: -1'):
        demo.pause(-1)

    with pytest.raises(ValueError, match='ms must be positive: 0'):
        demo.title('Chapter', ms=0)

    with pytest.raises(ValueError, match='ms must be positive: 0'):
        demo.narrate('Step', ms=0)

    with pytest.raises(ValueError, match='ms must be positive: 0'):
        demo.metrics('Totals', [], ms=0)

    with pytest.raises(ValueError, match='ms must be positive: 0'):
        demo.spotlight(locator.as_locator(), ms=0)


def test_a_goto_without_a_route_is_refused() -> None:
    demo, _, application, _ = demo_build()

    with pytest.raises(ValueError, match='route must not be empty'):
        demo.goto('')

    assert application.logins == []


def test_the_video_sink_takes_the_quality_settings(demos_root: Path) -> None:
    page = FakePage()
    renderer = FakeFrameRenderer(fps=30)
    config = DemoConfig(mode='narrate', quality='low', video=True)

    renderer_register(page.as_page(), cast('FrameRenderer', renderer))

    try:
        Demo(page.as_page(), FakeApplication(), name='demo', config=config)
    finally:
        renderer_unregister(page.as_page())

    sink = renderer.sinks[0]

    assert sink._crf == VIDEO_QUALITIES['low'].crf
    assert sink._fps == 30
    assert sink._preset == VIDEO_QUALITIES['low'].preset
