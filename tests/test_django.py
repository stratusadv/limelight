from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing_extensions import cast

from limelight.application import Application
from limelight.django import AUTH_BACKEND_FALLBACK, DjangoApplication, LiveServer, SessionUser, auth_backend


class FakeLiveServer:
    url = 'http://localhost:9999'


class FakeUser:
    pk = 7

    def get_session_auth_hash(self) -> str:
        return 'hash'


def test_auth_backend_uses_first_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(AUTHENTICATION_BACKENDS=['app.auth.PortalBackend'])

    monkeypatch.setattr('limelight.django.settings', settings_stub)

    assert auth_backend() == 'app.auth.PortalBackend'


def test_auth_backend_falls_back_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(AUTHENTICATION_BACKENDS=[])

    monkeypatch.setattr('limelight.django.settings', settings_stub)

    assert auth_backend() == AUTH_BACKEND_FALLBACK


def test_django_application_satisfies_protocol() -> None:
    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())

    assert isinstance(application, Application)


def test_fakes_satisfy_their_protocols() -> None:
    assert isinstance(FakeLiveServer(), LiveServer)
    assert isinstance(FakeUser(), SessionUser)


def test_with_user_builds_new_application() -> None:
    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())
    user_new = FakeUser()

    application_new = application.with_user(user_new)

    assert application_new is not application
    assert application_new.user is user_new
    assert application_new.live_server is application.live_server


def test_with_user_rejects_non_session_user() -> None:
    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())

    with pytest.raises(TypeError, match='SessionUser'):
        application.with_user(object())


def test_live_server_required() -> None:
    with pytest.raises(ValueError, match='live_server'):
        DjangoApplication(live_server=cast('LiveServer', None), user=FakeUser())


def test_user_required() -> None:
    with pytest.raises(ValueError, match='user'):
        DjangoApplication(live_server=FakeLiveServer(), user=cast('SessionUser', None))
