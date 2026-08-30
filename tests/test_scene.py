from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing_extensions import override

from limelight.config import DemoConfig
from limelight.demo import Demo
from limelight.scene import Scene

from fakes import FakeApplication, FakeLocator, FakeNarrator, FakePage


class DashboardScene(Scene):
    route = 'home:dashboard'

    def __init__(self, demo: Demo) -> None:
        super().__init__(demo)

        self.ready_check_count = 0

    @override
    def expect_ready(self) -> None:
        self.ready_check_count += 1


class PlainScene(Scene):
    route = 'home:dashboard'


class RoutelessScene(Scene):
    pass


def demo_build() -> tuple[Demo, FakeApplication]:
    application = FakeApplication()
    demo = Demo(FakePage().as_page(), application, name='demo', config=DemoConfig())

    return demo, application


def test_open_navigates_and_checks_readiness() -> None:
    demo, application = demo_build()
    scene = DashboardScene(demo)

    result = scene.open()

    assert result is scene
    assert application.url_requests == [('home:dashboard', {})]
    assert scene.ready_check_count == 1


def test_open_forwards_url_kwargs() -> None:
    demo, application = demo_build()

    DashboardScene(demo).open(pk=7)

    assert application.url_requests == [('home:dashboard', {'pk': 7})]


def test_open_requires_route() -> None:
    demo, _ = demo_build()

    with pytest.raises(ValueError, match='route'):
        RoutelessScene(demo).open()


def test_the_default_readiness_check_does_nothing() -> None:
    demo, application = demo_build()
    scene = PlainScene(demo)

    assert scene.open() is scene
    assert application.url_requests == [('home:dashboard', {})]


def actor_build() -> tuple[PlainScene, FakeNarrator, FakePage]:
    page = FakePage()
    narrator = FakeNarrator()

    demo = Demo(
        page.as_page(),
        FakeApplication(),
        name='demo',
        config=DemoConfig(),
        narrator=narrator.as_narrator(),
    )

    return PlainScene(demo), narrator, page


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(to_be_visible=lambda timeout: None)


def test_an_action_holds_after_it_lands() -> None:
    scene, narrator, _ = actor_build()
    locator = FakeLocator().as_locator()

    scene._click(locator)
    scene._fill(locator, 'Chinook')
    scene._select(locator, 'Alberta')
    scene._check(locator)
    scene._hover(locator)
    scene._press(locator, 'Enter')

    kinds = [call[0] for call in narrator.calls]

    assert kinds == [
        'click',
        'pause',
        'fill',
        'pause',
        'select',
        'pause',
        'check',
        'pause',
        'hover',
        'pause',
        'press',
        'pause',
    ]


def test_a_tab_is_opened_by_its_role_and_name() -> None:
    scene, _, page = actor_build()

    scene._tab('Stations')

    assert page.role_queries == [('tab', 'Stations', False)]


def test_a_teach_focus_reveals_without_clicking() -> None:
    scene, narrator, _ = actor_build()

    scene._teach_focus(
        FakeLocator().as_locator(),
        headline='The stock number',
        label='002012',
        body='The dealership prints this one.',
        step='Detail',
    )

    narration = ('The stock number', 'The dealership prints this one.', 'Detail')

    assert narrator.calls[0][0:4] == ('narrate', *narration)
    assert narrator.calls[1][2] == '002012'
    assert not any(call[0] == 'click' for call in narrator.calls)


def test_a_teach_focus_with_only_a_label_spotlights() -> None:
    scene, narrator, _ = actor_build()

    scene._teach_focus(FakeLocator().as_locator(), label='002012')

    kinds = [call[0] for call in narrator.calls]

    assert kinds == ['spotlight']
    assert narrator.calls[0][2] == '002012'


def test_a_teach_focus_with_nothing_to_say_stays_silent() -> None:
    scene, narrator, _ = actor_build()

    scene._teach_focus(FakeLocator().as_locator())

    assert narrator.calls == []


def test_a_teach_click_reveals_then_clicks() -> None:
    scene, narrator, _ = actor_build()

    scene._teach_click(FakeLocator().as_locator(), headline='Approve it', label='Approve')

    kinds = [call[0] for call in narrator.calls]

    assert kinds == ['narrate', 'spotlight', 'click', 'pause']


@pytest.fixture(autouse=True)
def _expect_stubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.demo.expect', expect_stub)
