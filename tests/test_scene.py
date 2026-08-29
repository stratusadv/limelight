from __future__ import annotations

import pytest

from typing_extensions import override

from limelight.config import DemoConfig
from limelight.demo import Demo
from limelight.scene import Scene

from fakes import FakeApplication, FakePage


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
