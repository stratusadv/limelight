from __future__ import annotations

import contextlib
import json

from collections.abc import Mapping
from typing import TYPE_CHECKING

from playwright.sync_api import Error as PlaywrightError

from limelight.overlay.assets import OVERLAY_CSS, OVERLAY_JAVASCRIPT
from limelight.theme import Theme

if TYPE_CHECKING:
    from playwright.sync_api import Page

    from limelight.config import DemoConfig


EVALUATE_ATTEMPT_COUNT = 3
NAVIGATION_ERROR_FRAGMENT = 'Execution context was destroyed'
NAVIGATION_SETTLE_TIMEOUT_MS = 5000


class Bridge:
    """
    A channel between the demo and the overlay running inside the page.

    This class installs the overlay on every document the page loads and forwards
    calls into it, reinstalling when a navigation has torn it down.
    """

    def __init__(self, page: Page, config: DemoConfig, theme: Theme | None = None) -> None:
        """
        The constructor for the Bridge class.

        :param page: The page the overlay is installed on.
        :param config: The configuration the overlay is built from.
        :param theme: The palette the overlay draws with, or None for the default.
        """

        theme_applied = theme if theme is not None else Theme()

        self._page = page

        self._settings: dict[str, object] = {
            'css': OVERLAY_CSS,
            'theme': theme_applied.payload(),
            'controls': config.controls,
            'speedFactor': config.speed_factor,
            'stepMode': config.present,
        }

        self.install(page)

    def _evaluate(self, expression: str, argument: object = None) -> object:
        """
        A method that evaluates an expression in the page and retries across navigations.

        A navigation destroys the execution context mid-call, which surfaces as an
        error rather than as a result, so the call is retried once the new document has
        loaded. Any other error is re-raised, because retrying a broken expression only
        delays the failure.

        :param expression: The JavaScript expression to evaluate.
        :param argument: The value passed to the expression.
        :return: The result of the expression.
        :raises RuntimeError: If every attempt is lost to a navigation.
        """

        for _ in range(EVALUATE_ATTEMPT_COUNT):
            try:
                result = self._page.evaluate(expression, argument)
            except PlaywrightError as error:
                if NAVIGATION_ERROR_FRAGMENT not in str(error):
                    raise
            else:
                return result

            with contextlib.suppress(PlaywrightError):
                self._page.wait_for_load_state(
                    'domcontentloaded',
                    timeout=NAVIGATION_SETTLE_TIMEOUT_MS,
                )

        message = f'the page navigated away on {EVALUATE_ATTEMPT_COUNT} consecutive evaluations'
        raise RuntimeError(message)

    @property
    def page(self) -> Page:
        """
        A property that exposes the page the overlay is installed on.

        :return: The page the bridge currently drives.
        """

        return self._page

    def call(self, function_name: str, argument: Mapping[str, object] | None = None) -> object:
        """
        A method that calls a function on the overlay API.

        The expression returns null when the overlay is absent, which is distinct from
        a function that returns null itself, so a missing overlay is reinstalled and
        the call retried once.

        :param function_name: The name of the function on the overlay API.
        :param argument: The value passed to the function.
        :return: The result of the function, or None if it returned nothing.
        :raises RuntimeError: If the overlay is still unreachable after a reinstall.
        """

        expression = (
            'async (argument) => window.__limelight'
            f' ? {{result: await window.__limelight.{function_name}(argument)}}'
            ' : null'
        )

        outcome = self._evaluate(expression, argument)

        if outcome is None:
            self.ensure()

            outcome = self._evaluate(expression, argument)

        if outcome is None:
            message = f'window.__limelight.{function_name} is unreachable after install'
            raise RuntimeError(message)

        if isinstance(outcome, Mapping):
            return outcome.get('result')

        return None

    def ensure(self) -> None:
        """A method that installs the overlay into the current document."""

        self._page.wait_for_selector('body', state='attached')
        self._evaluate(OVERLAY_JAVASCRIPT, self._settings)

    def install(self, page: Page) -> None:
        """
        A method that arms the overlay to install itself on each document load.

        :param page: The page the init script is registered on.
        """

        argument = json.dumps(self._settings)

        script = (
            'document.addEventListener("DOMContentLoaded", () => {'
            f'({OVERLAY_JAVASCRIPT})({argument});'
            '});'
        )

        page.add_init_script(script)

    def read(self, function_name: str) -> Mapping[str, object] | None:
        """
        A method that calls an overlay function expected to return state.

        :param function_name: The name of the function on the overlay API.
        :return: The state the function returned, or None if it returned something else.
        """

        state = self.call(function_name)

        if isinstance(state, Mapping):
            return state

        return None

    def switch_page(self, page: Page) -> None:
        """
        A method that points the bridge at a different page.

        :param page: The page later calls are made against.
        """

        self.install(page)

        self._page = page
