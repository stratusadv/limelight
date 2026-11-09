# Django

## Overview

The `limelight.django` package adapts a demo to a Django project. A demo addresses pages by URL name and signs in by writing a session rather than filling the login form.

## Set Up

1. [Install the package](install.md) with both extras.
2. Register both plugins in the root `conftest.py`.

    ```python title="conftest.py"
    pytest_plugins = ['limelight.pytest_plugin', 'limelight.django.pytest_plugin']
    ```

3. Write the demo with a [`DjangoApplication`][limelight.django.DjangoApplication]. The route is a URL name, and the keyword arguments reach `reverse`. A `goto` with no `user` raises `TypeError`.

    ```python
    from limelight import Demo
    from limelight.django import DjangoApplication


    def test_order_approval_demo(page, live_server, admin_user):
        application = DjangoApplication(live_server=live_server)
        demo = Demo(page, application, name='order-approval', user=admin_user)

        demo.goto('order', pk=214, query={'tab': 'payments'})
    ```

## How It Works

The plugin runs one live server for the session and gives each page a navigation timeout of 60 seconds. A test database that SQLite holds in memory is served one request at a time, because a second connection to it sees an empty database rather than the rows the test wrote. The plugin also sets `DJANGO_ALLOW_ASYNC_UNSAFE` when it is unset, because Playwright runs an event loop on the test thread and Django refuses a synchronous database call from that thread.

## Helpers

| Name | Description |
|------|-------------|
| [`url_kwargs_defaults`][limelight.django.DjangoApplication.url_kwargs_defaults] | The method supplies arguments each route takes, such as a tenant. Override it on a `DjangoApplication` subclass. |
| [`force_login`][limelight.django.force_login] | The function signs a user in by writing a session and its cookie. |
| [`sign_in`][limelight.django.sign_in] | The function signs a user in through the login form. The `LOGIN_URL` setting has to be a URL name. |
| [`visit`][limelight.django.visit] | The function signs a user in and opens a route, with no `Demo`. |
| [`wait_until`][limelight.django.wait_until] | The function polls a database condition and survives a dropped connection. |
| [`database_resilient`][limelight.django.database_resilient] | The function wraps a condition the same way, for `demo.wait_until`. |
