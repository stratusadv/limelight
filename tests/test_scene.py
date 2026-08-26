from __future__ import annotations

import pytest

from typing import override

from limelight.scene import Scene
from limelight.session import DemoSession

from fakes import FakeApplication, FakePage, FakePresenter


class DashboardScene(Scene):
    route = 'home:dashboard'

    def __init__(self, demo: DemoSession) -> None:
        super().__init__(demo)

        self.ready_check_count = 0

    @override
    def expect_ready(self) -> None:
        self.ready_check_count += 1


class RoutelessScene(Scene):
    pass


def session_build() -> tuple[DemoSession, FakeApplication]:
    application = FakeApplication()
    session = DemoSession(FakePage().as_page(), application, presenter=FakePresenter())

    return session, application


def test_open_navigates_and_checks_readiness() -> None:
    session, application = session_build()
    scene = DashboardScene(session)

    result = scene.open()

    assert result is scene
    assert application.url_requests == [('home:dashboard', {})]
    assert scene.ready_check_count == 1


def test_open_forwards_url_kwargs() -> None:
    session, application = session_build()

    DashboardScene(session).open(pk=7)

    assert application.url_requests == [('home:dashboard', {'pk': 7})]


def test_open_requires_route() -> None:
    session, _ = session_build()

    with pytest.raises(ValueError, match='route'):
        RoutelessScene(session).open()
