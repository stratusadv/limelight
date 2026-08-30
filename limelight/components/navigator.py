from __future__ import annotations

import contextlib

from typing import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from limelight.demo import Demo


NAVIGATION_WAIT_TIMEOUT_MS = 5000

SCROLL_INTO_VIEW_SCRIPT = 'el => el.scrollIntoView({block: "center"})'


class Navigator:
    """
    A narrated driver for a navigation menu.

    This class opens a destination by the text a viewer reads on its link,
    narrating the move, spotlighting the link, and waiting for the page it leads
    to rather than assuming the click landed. A menu long enough to scroll is
    brought into view first, because a spotlight drawn over an offscreen link
    highlights nothing.

    The default selector describes a plain anchor. A project whose menu is drawn
    differently subclasses this and overrides the selector, and names its
    destinations as methods so a demo reads as prose:

    ::

        class SideNavigator(Navigator):
            link_selector = 'a.nav-side-link'

            def open_orders(self, *, headline: str = 'Open the order list') -> None:
                self.to('Orders', headline=headline)
    """

    body = ''
    link_selector = 'a'
    shot_prefix = 'nav'
    step = 'Navigating'
    wait_timeout_ms = NAVIGATION_WAIT_TIMEOUT_MS

    def __init__(self, demo: Demo) -> None:
        """
        The constructor for the Navigator class.

        :param demo: The demo driving the browser.
        """

        self.demo = demo

    def _scrolled_into_view(self, link: Locator) -> None:
        """
        A method that brings a link into view, tolerating a menu that cannot scroll.

        :param link: The locator for the link.
        """

        with contextlib.suppress(PlaywrightTimeoutError):
            link.evaluate(SCROLL_INTO_VIEW_SCRIPT, timeout=self.wait_timeout_ms)

    def _settled(self, url_before: str) -> None:
        """
        A method that waits for the click to land on a new page.

        A destination that re-renders in place never changes the URL, so the wait
        for a new one is bounded and its expiry is not an error.

        :param url_before: The URL the page was on before the click.
        """

        with contextlib.suppress(PlaywrightTimeoutError):
            self.demo.page.wait_for_url(
                lambda url: url != url_before,
                timeout=self.wait_timeout_ms,
            )

        self.demo.page.wait_for_load_state('domcontentloaded')

    def link(self, text: str) -> Locator:
        """
        A method that gets the menu link a text names.

        :param text: The text shown on the link.
        :return: The locator for the link.
        """

        links = self.demo.page.locator(self.link_selector).filter(has_text=text)

        return links.filter(visible=True).first

    def to(self, text: str, *, headline: str = '', body: str = '', shot: bool = True) -> None:
        """
        A method that narrates a move to one destination of the menu.

        :param text: The text shown on the link.
        :param headline: The narration headline, or an empty string to stay silent.
        :param body: The narration body, defaulting to the one the class carries.
        :param shot: Whether a screenshot is captured before the click.
        :raises AssertionError: If the link never appears.
        """

        link = self.link(text)

        expect(link).to_be_visible(timeout=self.wait_timeout_ms)

        if headline:
            self.demo.narrate(headline, step=self.step, body=body or self.body)

        self._scrolled_into_view(link)

        self.demo.spotlight(link, label=f'Click "{text}"', scroll=False)

        if shot:
            slug = text.lower().replace(' ', '-')

            self.demo.screenshot(f'{self.shot_prefix}-{slug}')

        url_before = self.demo.page.url

        self.demo.click(link)

        self._settled(url_before)
