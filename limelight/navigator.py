from __future__ import annotations

import contextlib

from typing_extensions import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

from limelight.actor import Actor

if TYPE_CHECKING:
    from playwright.sync_api import Locator


NAV_KIND_BUTTON = 'button'
NAV_KIND_LINK = 'link'
NAV_KIND_NAV = 'nav'
NAV_KIND_TAB = 'tab'
NAV_KINDS = (NAV_KIND_BUTTON, NAV_KIND_LINK, NAV_KIND_NAV, NAV_KIND_TAB)
NAV_KINDS_ROUTED = (NAV_KIND_LINK, NAV_KIND_NAV)
NAV_WAIT_TIMEOUT_MS = 5000


class Navigator(Actor):
    nav_link_selector = ''

    def _target(self, kind: str, text: str) -> Locator:
        if kind not in NAV_KINDS:
            options = ', '.join(NAV_KINDS)

            message = f'kind must be one of: {options} (got "{kind}")'
            raise ValueError(message)

        if kind == NAV_KIND_TAB:
            return self._demo.page.get_by_role('tab', name=text)

        if kind == NAV_KIND_NAV:
            return self._target_nav(text)

        if kind == NAV_KIND_BUTTON:
            return self._target_button(text)

        return self._target_link(text)

    def _target_button(self, text: str) -> Locator:
        buttons = self._demo.page.get_by_role('button', name=text, exact=True)

        return buttons.filter(visible=True).first

    def _target_link(self, text: str) -> Locator:
        page = self._demo.page
        fallback = page.get_by_role('link', name=text).filter(visible=True).first

        expect(fallback).to_be_visible(timeout=NAV_WAIT_TIMEOUT_MS)

        exact = page.get_by_role('link', name=text, exact=True).filter(visible=True)

        if exact.count() > 0:
            return exact.first

        return fallback

    def _target_nav(self, text: str) -> Locator:
        if not self.nav_link_selector:
            message = f'{type(self).__name__}.nav_link_selector must be set before nav trail steps'
            raise ValueError(message)

        links = self._demo.page.locator(self.nav_link_selector).filter(has_text=text)

        return links.filter(visible=True).first

    def _trail_step(self, kind: str, text: str) -> None:
        target = self._target(kind, text)
        label = f'Click "{text}"'
        routed = kind in NAV_KINDS_ROUTED

        if kind == NAV_KIND_NAV:
            with contextlib.suppress(PlaywrightTimeoutError):
                target.evaluate(
                    'el => el.scrollIntoView({block: "center"})',
                    timeout=NAV_WAIT_TIMEOUT_MS,
                )

            self._demo.spotlight(target, label=label, scroll=False)
        else:
            self._demo.spotlight(target, label=label)

        if routed:
            self._demo.shot(f'nav-{text.lower().replace(" ", "-")}')

        self._demo.clear_spotlight()

        if routed:
            self._trail_step_click_routed(target)
        else:
            self._trail_step_click(target)

    def _trail_step_click(self, target: Locator) -> None:
        self._demo.click(target)
        self._demo.hold()

    def _trail_step_click_routed(self, target: Locator) -> None:
        page = self._demo.page
        url_current = page.url

        self._demo.click(target)

        with contextlib.suppress(PlaywrightTimeoutError):
            page.wait_for_url(
                lambda url, url_current=url_current: url != url_current,
                timeout=NAV_WAIT_TIMEOUT_MS,
            )

        page.wait_for_load_state('domcontentloaded')
        self._demo.hold()

    def to(self, *trail: tuple[str, str], headline: str = '', shot: str = '') -> None:
        if headline:
            self._demo.narrate(
                headline,
                step='Navigate',
                body='Click through the app to get there.',
            )

        for kind, text in trail:
            self._trail_step(kind, text)

        if shot:
            self._demo.shot(shot)
