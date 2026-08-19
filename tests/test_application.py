from __future__ import annotations

import pytest

from limelight.application import Application, StaticApplication

from fakes import FakePage


def test_static_application_satisfies_protocol() -> None:
    application = StaticApplication(base_url='http://stage.test')

    assert isinstance(application, Application)


def test_base_url_empty_rejected() -> None:
    with pytest.raises(ValueError, match='base_url'):
        StaticApplication(base_url='  ')


def test_base_url_trailing_slash_stripped() -> None:
    application = StaticApplication(base_url='http://stage.test/')

    assert application.url('orders/', {}) == 'http://stage.test/orders/'


def test_url_formats_kwargs_into_route() -> None:
    application = StaticApplication(base_url='http://stage.test')

    assert application.url('/orders/{pk}/', {'pk': 7}) == 'http://stage.test/orders/7/'


def test_login_callable_receives_page_and_user() -> None:
    logins: list[tuple[object, object]] = []
    user = object()

    def login(page: object, login_user: object) -> None:
        entry = (page, login_user)
        logins.append(entry)

    page = FakePage()
    application = StaticApplication(base_url='http://stage.test', login=login, user=user)

    application.login(page.as_page())

    assert logins == [(page, user)]


def test_login_without_callable_is_a_no_op() -> None:
    application = StaticApplication(base_url='http://stage.test')

    application.login(FakePage().as_page())


def test_with_user_keeps_base_url_and_login() -> None:
    logins: list[tuple[object, object]] = []

    def login(page: object, login_user: object) -> None:
        entry = (page, login_user)
        logins.append(entry)

    application = StaticApplication(base_url='http://stage.test', login=login)
    user = object()

    application_new = application.with_user(user)

    assert application_new is not application
    assert application_new.base_url == 'http://stage.test'
    assert application_new.user is user

    application_new.login(FakePage().as_page())

    assert len(logins) == 1
