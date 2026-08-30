from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Self

    from playwright.sync_api import Locator

    from limelight.demo import Demo


class Scene:
    """
    A page object for a single screen of a demo.

    This class pairs a route with the assertions that prove the screen has
    loaded. A subclass sets the route and overrides expect_ready().

    The protected helpers are the vocabulary an actor is written in. Each one
    performs an action through the demo and then holds, so a narrated run shows
    the drawn pointer land before the next step begins and a silent run pays
    nothing for the hold. A scene calls them rather than a Playwright locator
    method, because a bare click moves the real mouse without moving the drawn
    one.

    ::

        class OrderScene(Scene):
            route = 'sales:order:page:list'

            def expect_ready(self) -> None:
                expect(self.search_field).to_be_visible()

            def search(self, text: str) -> None:
                self._teach_focus(self.search_field, headline='Search', label='Search')

                self._fill(self.search_field, text)
    """

    route = ''

    def __init__(self, demo: Demo) -> None:
        """
        The constructor for the Scene class.

        :param demo: The demo that drives the browser for this scene.
        """

        self.demo = demo

    def _check(self, locator: Locator) -> None:
        """
        A method that ticks a checkbox and holds.

        :param locator: The locator for the checkbox.
        """

        self.demo.check(locator)
        self.demo.pause()

    def _click(self, locator: Locator, *, force: bool = False) -> None:
        """
        A method that clicks an element and holds.

        :param locator: The locator for the element to click.
        :param force: Whether to click without waiting for the element to be actionable.
        """

        self.demo.click(locator, force=force)
        self.demo.pause()

    def _fill(self, locator: Locator, value: str) -> None:
        """
        A method that puts text into a field and holds.

        :param locator: The locator for the field.
        :param value: The text to put into the field.
        """

        self.demo.fill(locator, value)
        self.demo.pause()

    def _hover(self, locator: Locator) -> None:
        """
        A method that hovers over an element and holds.

        :param locator: The locator for the element to hover over.
        """

        self.demo.hover(locator)
        self.demo.pause()

    def _press(self, locator: Locator, key: str) -> None:
        """
        A method that presses a key on an element and holds.

        :param locator: The locator for the element the key is pressed on.
        :param key: The key to press.
        """

        self.demo.press(locator, key)
        self.demo.pause()

    def _select(self, locator: Locator, option_label: str) -> None:
        """
        A method that picks an option by its label and holds.

        :param locator: The locator for the select element.
        :param option_label: The visible text of the option to pick.
        """

        self.demo.select(locator, option_label)
        self.demo.pause()

    def _tab(self, name: str) -> None:
        """
        A method that opens the tab a name identifies.

        :param name: The text shown on the tab.
        """

        tab = self.demo.page.get_by_role('tab', name=name)

        self._click(tab)

    def _teach_click(
        self,
        locator: Locator,
        *,
        headline: str = '',
        label: str = '',
        body: str = '',
        step: str = '',
    ) -> None:
        """
        A method that shows the viewer an element and then clicks it.

        :param locator: The locator for the element to show and click.
        :param headline: The narration headline, or an empty string for none.
        :param label: The caption shown beside the element.
        :param body: The narration body shown under the headline.
        :param step: The step label the narration carries.
        :raises AssertionError: If the element is narrated and never appears.
        """

        self._teach_focus(locator, headline=headline, label=label, body=body, step=step)

        self._click(locator)

    def _teach_focus(
        self,
        locator: Locator,
        *,
        headline: str = '',
        label: str = '',
        body: str = '',
        step: str = '',
    ) -> None:
        """
        A method that shows the viewer an element, once it is on the page.

        A headline narrates the element in full, and the element is waited for
        before anything is said about it, so the step is a barrier in a silent
        run as well as a caption in a narrated one. A label alone spotlights the
        element without narration, and neither says nothing at all.

        :param locator: The locator for the element to show.
        :param headline: The narration headline, or an empty string for none.
        :param label: The caption shown beside the element.
        :param body: The narration body shown under the headline.
        :param step: The step label the narration carries.
        :raises AssertionError: If the element is narrated and never appears.
        """

        if headline:
            self.demo.reveal(locator, headline=headline, body=body, step=step, label=label)
        elif label:
            self.demo.spotlight(locator, label=label)

    def expect_ready(self) -> None:
        """
        A method that waits until the scene has finished loading.

        The base implementation does nothing, so a scene that needs to settle
        before the next step overrides this with its own assertions.
        """

    def open(
        self,
        *,
        query: Mapping[str, object] | None = None,
        **url_kwargs: object,
    ) -> Self:
        """
        A method that navigates to the scene route and waits for it to be ready.

        :param query: The query string parameters appended to the URL, or None for none.
        :param url_kwargs: The arguments used to reverse the route into a URL.
        :return: The scene itself, so calls can be chained.
        :raises ValueError: If the route has not been set on the subclass.
        """

        if not self.route:
            message = f'{type(self).__name__}.route must be set before open()'
            raise ValueError(message)

        self.demo.goto(self.route, query=query, **url_kwargs)
        self.expect_ready()

        return self
