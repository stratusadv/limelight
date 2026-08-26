from __future__ import annotations

from typing import TYPE_CHECKING, cast, override

from limelight.config import DEMO_MODE_NARRATE, DemoConfig
from limelight.frames import renderer_register, renderer_unregister
from limelight.navigator import Navigator
from limelight.presenter import PresenterNarrated, PresenterSilent
from limelight.session import DemoSession

from fakes import FakeApplication, FakeFrameRenderer, FakeLocator, FakePage, FakePresenter

if TYPE_CHECKING:
    from pathlib import Path

    from limelight.frames import FrameRenderer


class RecordingNavigator(Navigator):
    nav_link_selector = '.nav-link'


class RecordingSession(DemoSession):
    navigator_class = RecordingNavigator


class PreparingSession(DemoSession):
    @override
    def scenes_prepare(self) -> None:
        self.prepared_navigator = self.nav


def session_build(
    page: FakePage | None = None,
) -> tuple[DemoSession, FakePage, FakeApplication, FakePresenter]:
    page = page if page is not None else FakePage()
    application = FakeApplication()
    presenter = FakePresenter()
    session = DemoSession(page.as_page(), application, presenter=presenter)

    return session, page, application, presenter


def test_init_disables_window_print() -> None:
    _, page, _, _ = session_build()

    assert page.init_scripts == ['window.print = () => {};']


def test_goto_logs_in_then_navigates() -> None:
    session, page, application, _ = session_build()

    session.goto('home:dashboard')

    assert application.login_pages == [page]
    assert application.url_requests == [('home:dashboard', {})]
    assert page.goto_urls == ['http://stage.test/home:dashboard']


def test_goto_forwards_url_kwargs() -> None:
    session, _, application, _ = session_build()

    session.goto('order:detail', pk=7)

    assert application.url_requests == [('order:detail', {'pk': 7})]


def test_facade_delegates_to_presenter() -> None:
    session, _, _, presenter = session_build()

    session.narrate('Welcome', body='Hello.')
    session.hold()
    session.shot('welcome')
    session.clear()

    call_names = [call[0] for call in presenter.calls]

    assert call_names == ['narrate', 'hold', 'shot', 'clear']


def test_actions_delegate_to_presenter() -> None:
    session, _, _, presenter = session_build()
    locator = FakeLocator()

    session.click(locator.as_locator())
    session.fill(locator.as_locator(), 'hello')
    session.select(locator.as_locator(), 'Approved')

    call_names = [call[0] for call in presenter.calls]

    assert call_names == ['click', 'fill', 'select']


def test_new_actions_delegate_to_presenter() -> None:
    session, _, _, presenter = session_build()
    locator = FakeLocator()
    thumb = FakeLocator()

    session.check(locator.as_locator())
    session.hover(locator.as_locator())
    session.press(locator.as_locator(), 'Enter')
    session.slide(track=locator.as_locator(), thumb=thumb.as_locator())
    session.uncheck(locator.as_locator())

    call_names = [call[0] for call in presenter.calls]

    assert call_names == ['check', 'hover', 'press', 'slide', 'uncheck']


def test_window_print_stub_can_be_disabled() -> None:
    class PrintingSession(DemoSession):
        window_print_stubbed = False

    page = FakePage()

    PrintingSession(page.as_page(), FakeApplication(), presenter=FakePresenter())

    assert page.init_scripts == []


def test_login_as_switches_application_and_logs_in() -> None:
    session, page, application, _ = session_build()
    user = object()

    session.login_as(user)

    application_new = session.application

    assert application_new is not application
    assert isinstance(application_new, FakeApplication)
    assert application_new.user is user
    assert application_new.login_pages == [page]


def test_start_silent_builds_null_presenter() -> None:
    session = DemoSession.start(
        FakePage().as_page(),
        FakeApplication(),
        shot_directory_name='demo',
        config=DemoConfig(),
    )

    assert isinstance(session.presenter, PresenterSilent)


def test_start_narrated_builds_narrated_presenter() -> None:
    config = DemoConfig(mode=DEMO_MODE_NARRATE)

    session = DemoSession.start(
        FakePage().as_page(),
        FakeApplication(),
        shot_directory_name='demo',
        config=config,
    )

    assert isinstance(session.presenter, PresenterNarrated)


def test_init_honors_injected_presenter() -> None:
    presenter = FakePresenter()

    session = DemoSession(FakePage().as_page(), FakeApplication(), presenter=presenter)

    assert session.presenter is presenter


def test_scenes_prepare_runs_after_the_navigator_is_built() -> None:
    session = PreparingSession(FakePage().as_page(), FakeApplication(), presenter=FakePresenter())

    assert session.prepared_navigator is session.nav


def test_subclass_navigator_class_is_used() -> None:
    session = RecordingSession(FakePage().as_page(), FakeApplication(), presenter=FakePresenter())

    assert isinstance(session.nav, RecordingNavigator)


def test_use_page_switches_page_everywhere() -> None:
    session, _, _, presenter = session_build()
    page_second = FakePage()

    session.use_page(page_second.as_page())

    assert session.page is page_second
    assert presenter.calls == [('use_page', page_second)]


def test_use_page_disables_window_print_on_new_page() -> None:
    session, _, _, _ = session_build()
    page_second = FakePage()

    session.use_page(page_second.as_page())

    assert page_second.init_scripts == ['window.print = () => {};']


def test_start_hands_the_registered_renderer_to_the_presenter(tmp_path: Path) -> None:
    page = FakePage()
    renderer = FakeFrameRenderer()
    config = DemoConfig(mode=DEMO_MODE_NARRATE, video=True)

    renderer_register(page.as_page(), cast('FrameRenderer', renderer))

    try:
        session = DemoSession.start(
            page.as_page(),
            FakeApplication(),
            shot_directory_name=str(tmp_path / 'demo'),
            config=config,
        )
    finally:
        renderer_unregister(page.as_page())

    assert isinstance(session.presenter, PresenterNarrated)
    assert len(renderer.sinks) == 1
