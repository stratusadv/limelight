from __future__ import annotations

import contextlib
import time

from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

from limelight import barriers
from limelight.artifacts import DIRECTORY_ROOT, TRANSCRIPT_FILE_NAME, VIDEO_FILE_NAME
from limelight.capture.camera import Camera
from limelight.capture.renderer import renderer_for
from limelight.capture.sinks import VideoSink
from limelight.config import DemoConfig
from limelight.ffmpeg import Ffmpeg
from limelight.javascript import script
from limelight.narrator import Silent
from limelight.overlay.bridge import Bridge
from limelight.overlay.cursor import Cursor
from limelight.overlay.keyboard import Keyboard, key_masked, value_masked
from limelight.overlay.overlay import Overlay
from limelight.overlay.playback import Playback
from limelight.transcript import EventName, Transcript, cue_text
from limelight.limits import ELEMENT_WAIT_TIMEOUT_MS, HOLD_MS_MAX, SPEED_FACTOR_MAX

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from playwright.sync_api import Locator, Page

    from limelight.application import Application
    from limelight.capture.renderer import FrameRenderer
    from limelight.ledger import Ledger
    from limelight.narrator import Narrator
    from limelight.theme import Theme


FOLLOW_TIMEOUT_MS = 30_000

LOCATOR_LABEL_SCRIPT = script('locator_label.js')
LOCATOR_LABEL_TIMEOUT_MS = 2000

LOGIN_SETTLE_TIMEOUT_MS = 5000

PRINT_STUB_SCRIPT = 'window.print = () => {};'


def _frames_elapsed_seconds(renderer: FrameRenderer) -> float:
    """
    A function that reads how much footage a renderer has captured.

    :param renderer: The renderer whose frames are counted.
    :return: The seconds of footage the captured frames cover.
    :raises RuntimeError: If the renderer reports negative footage.
    """

    seconds = renderer.frame_count / renderer.fps

    if seconds < 0:
        message = f'the renderer reports negative footage: {seconds}s'
        raise RuntimeError(message)

    return seconds


def _hold_ms_validate(hold_ms: int | None) -> None:
    """
    A function that rejects a hold duration outside the range a demo can play.

    :param hold_ms: The duration asked for, or None to accept the default.
    :raises ValueError: If the duration is not positive, or passes the hold limit.
    """

    if hold_ms is None:
        return

    if hold_ms < 1:
        message = f'hold_ms must be positive: {hold_ms}'
        raise ValueError(message)

    if hold_ms > HOLD_MS_MAX:
        message = f'hold_ms must not exceed {HOLD_MS_MAX}: {hold_ms}'
        raise ValueError(message)


class Demo:
    """
    A driver for one recorded walkthrough of an application.

    This class is the surface a test writes against. Each action is recorded to the
    transcript and then performed through the narrator, so the same script produces
    a silent test run, a narrated presentation, or a rendered video depending only
    on the configuration.
    """

    def __init__(
        self,
        page: Page,
        application: Application,
        *,
        name: str,
        config: DemoConfig | None = None,
        narrator: Narrator | None = None,
        theme: Theme | None = None,
        user: object = None,
    ) -> None:
        """
        The constructor for the Demo class.

        The print dialog is stubbed out on each document, because a page that calls
        print blocks the renderer behind a modal the demo has no way to dismiss.

        :param page: The page the demo drives.
        :param application: The application under test.
        :param name: The name of the demo, which names its directory under .demos.
        :param config: The configuration for the run, or None to read the environment.
        :param narrator: The narrator the actions are performed through, or None to build one.
        :param theme: The palette the overlay draws with, or None for the default.
        :param user: The user the demo is signed in as.
        :raises ValueError: If the name is empty.
        """

        if not name:
            message = 'name must not be empty; it names the directory under .demos/'
            raise ValueError(message)

        if config is None:
            config = DemoConfig.from_env()

        self.application = application
        self.config = config
        self.directory = Path(DIRECTORY_ROOT) / name
        self.page = page
        self.user = user

        self._renderer: FrameRenderer | None = None
        self._transcript: Transcript | None = None

        self._page_prepared(page)

        if config.narrated:
            if config.video:
                self._renderer = self._renderer_started()

            transcript_path = self.directory / TRANSCRIPT_FILE_NAME

            self._transcript = Transcript(transcript_path, clock=self._clock_built())

        self._narrator = narrator if narrator is not None else self._narrator_built(theme)

    def _clock_built(self) -> Callable[[], float]:
        """
        A method that picks the clock the transcript measures its offsets on.

        A rendered run advances the page one frame at a time, so its offsets are
        read off the frame count rather than the wall clock. A slow render measured
        on the wall clock leaves the subtitles and the voiceover running ahead of the
        footage.

        :return: The clock, in seconds.
        """

        renderer = self._renderer

        if renderer is None:
            return time.monotonic

        return partial(_frames_elapsed_seconds, renderer)

    def _hold_ms_for(self, hold_ms: int | None, detail: Mapping[str, object]) -> int | None:
        """
        A method that resolves the hold of a spoken cue.

        :param hold_ms: The hold the test asked for, or None for the default.
        :param detail: The fields of the cue, as recorded to the transcript.
        :return: The hold asked for, else the hold the configuration gives the cue, else None.
        :raises RuntimeError: If a configured hold scales past the playable range.
        """

        if hold_ms is not None:
            return hold_ms

        hold_ms_spoken = self.config.hold_ms_for(cue_text(detail))

        if hold_ms_spoken is None:
            return None

        hold_ms_scaled = max(1, round(hold_ms_spoken * self.config.speed_factor))

        if hold_ms_scaled > HOLD_MS_MAX * SPEED_FACTOR_MAX:
            message = f'the hold for a spoken cue passed the playable range: {hold_ms_scaled}ms'
            raise RuntimeError(message)

        return hold_ms_scaled

    def _narrator_built(self, theme: Theme | None) -> Narrator:
        """
        A method that builds the narrator the configuration calls for.

        :param theme: The palette the overlay draws with, or None for the default.
        :return: The overlay for a narrated run, or a silent narrator otherwise.
        """

        config = self.config

        if not config.narrated:
            return Silent(self.page)

        camera = Camera(self.page, self.directory) if config.shots else None
        bridge = Bridge(self.page, config, theme)
        playback = Playback(bridge, config, clock=self._renderer)
        cursor = Cursor(bridge, playback, visible=not config.cursor_hidden)
        keyboard = Keyboard(bridge, playback)

        return Overlay(bridge, playback, cursor, keyboard, camera=camera)

    def _record(self, event: EventName, detail: Mapping[str, object]) -> None:
        """
        A method that records one event, if the run keeps a transcript.

        :param event: The kind of action being recorded.
        :param detail: The fields describing the action.
        """

        if self._transcript is not None:
            self._transcript.record(event, detail)

    def _record_action(self, event: EventName, locator: Locator, **detail: object) -> None:
        """
        A method that records an action against the label of its target.

        :param event: The kind of action being recorded.
        :param locator: The locator for the element the action is performed on.
        :param detail: The further fields describing the action.
        """

        if self._transcript is not None:
            self._transcript.record(event, {'target': locator_label(locator), **detail})

    @staticmethod
    def _page_prepared(page: Page) -> None:
        """
        A method that installs the scripts run on each document the demo opens.

        :param page: The page the scripts are installed on.
        """

        page.add_init_script(PRINT_STUB_SCRIPT)

    def _page_settled(self) -> None:
        """
        A method that waits for the network to go quiet, and gives up quietly.

        A page that holds a long poll open never reaches an idle network, so the
        timeout is suppressed: the wait is there to let a redirect finish, not to
        assert anything about the page.
        """

        with contextlib.suppress(PlaywrightTimeoutError):
            self.page.wait_for_load_state('networkidle', timeout=LOGIN_SETTLE_TIMEOUT_MS)

    def _renderer_started(self) -> FrameRenderer:
        """
        A method that starts the frame renderer and the encoder behind it.

        :return: The renderer driving the capture.
        """

        quality = self.config.video_quality
        renderer = renderer_for(self.page)

        sink = VideoSink(
            self.directory / VIDEO_FILE_NAME,
            Ffmpeg(),
            crf=quality.crf,
            fps=renderer.fps,
            preset=quality.preset,
        )

        renderer.start(sink)

        return renderer

    def check(self, locator: Locator) -> None:
        """
        A method that checks a checkbox.

        :param locator: The locator for the checkbox.
        """

        self._record_action(EventName.CHECK, locator)
        self._narrator.check(locator)

    def click(self, locator: Locator, *, force: bool = False) -> None:
        """
        A method that clicks an element.

        :param locator: The locator for the element to click.
        :param force: Whether to click without waiting for the element to be actionable.
        """

        self._record_action(EventName.CLICK, locator)
        self._narrator.click(locator, force=force)

    def fill(self, locator: Locator, value: str) -> None:
        """
        A method that puts text into a field.

        :param locator: The locator for the field.
        :param value: The text to put into the field.
        """

        if self._transcript is not None:
            self._record_action(EventName.FILL, locator, value=value_masked(locator, value))

        self._narrator.fill(locator, value)

    def follow(
        self,
        locator: Locator,
        *,
        label: str = '',
        timeout_ms: int = FOLLOW_TIMEOUT_MS,
    ) -> None:
        """
        A method that clicks a link and waits out the page it leads to.

        A destination a viewer is meant to follow is reached by clicking, so the
        drawn pointer is over the link when it fires rather than jumping to a URL
        the viewer never saw. The click is retried, because a link bound to a
        client-side handler can be clicked before the handler is listening.

        :param locator: The locator for the link.
        :param label: The caption shown beside the link, or an empty string to
            highlight nothing.
        :param timeout_ms: The time each attempt waits for the navigation.
        :raises BarrierError: If the page never navigates.
        """

        if label:
            self.spotlight(locator, label=label)

        barriers.trigger_until_navigation(
            self.page,
            lambda: self.click(locator),
            timeout_ms=timeout_ms,
        )

    def goto(
        self,
        route: str,
        *,
        query: Mapping[str, object] | None = None,
        **url_kwargs: object,
    ) -> None:
        """
        A method that signs the user in and navigates to a route.

        The login runs before each navigation because a demo can cross into a page
        that clears the session, and a redirect to the login form would be recorded as
        the destination.

        :param route: The route to navigate to.
        :param query: The query string parameters appended to the URL, or None for none.
        :param url_kwargs: The arguments filled into the route.
        :raises ValueError: If the route is empty.
        """

        if not route.strip():
            message = f'route must not be empty (got "{route}")'
            raise ValueError(message)

        self._page_settled()
        self.application.login(self.page, self.user)

        url = self.application.url(route, **url_kwargs)

        query_text = '' if query is None else urlencode(query)

        if query_text:
            url = f'{url}?{query_text}'

        self.page.goto(url)

    def hover(self, locator: Locator) -> None:
        """
        A method that hovers over an element.

        :param locator: The locator for the element to hover over.
        """

        self._record_action(EventName.HOVER, locator)
        self._narrator.hover(locator)

    def login_as(self, user: object) -> None:
        """
        A method that signs a different user in for the rest of the demo.

        :param user: The user to sign in as.
        """

        self._page_settled()

        self.user = user
        self.application.login(self.page, user)

    def metrics(
        self,
        title: str,
        rows: list[Ledger.Row],
        *,
        kicker: str = '',
        subtitle: str = '',
        hold_ms: int | None = None,
    ) -> None:
        """
        A method that shows a table of before and after readings.

        :param title: The heading for the table.
        :param rows: The rendered comparison of each metric.
        :param kicker: The line above the heading.
        :param subtitle: The line below the heading.
        :param hold_ms: The time the table is held on screen, or None for the default.
        :raises ValueError: If the duration is not positive, or passes the hold limit.
        """

        _hold_ms_validate(hold_ms)

        detail = {
            'title': title,
            'kicker': kicker,
            'subtitle': subtitle,
            'rows': list(rows),
        }

        self._record(EventName.METRICS, detail)
        self._narrator.metrics(title, rows, kicker=kicker, subtitle=subtitle, hold_ms=hold_ms)

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        hold_ms: int | None = None,
    ) -> None:
        """
        A method that shows a caption over the page.

        :param title: The heading for the caption.
        :param body: The paragraph below the heading.
        :param step: The label naming where the demo is in its script.
        :param hold_ms: The time the caption is held on screen, or None for the default.
        :raises ValueError: If the duration is not positive, or passes the hold limit.
        """

        _hold_ms_validate(hold_ms)

        detail = {
            'title': title,
            'body': body,
            'step': step,
        }

        self._record(EventName.NARRATE, detail)

        hold_ms_resolved = self._hold_ms_for(hold_ms, detail)

        self._narrator.narrate(title, body=body, step=step, hold_ms=hold_ms_resolved)

    def pause(self, hold_ms: int | None = None) -> None:
        """
        A method that holds the demo without showing anything.

        :param hold_ms: The time to hold for, or None for the default.
        :raises ValueError: If the duration is not positive, or passes the hold limit.
        """

        _hold_ms_validate(hold_ms)

        self._narrator.pause(hold_ms)

    def press(self, locator: Locator, key: str) -> None:
        """
        A method that presses a key on an element.

        :param locator: The locator for the element the key is pressed on.
        :param key: The key to press.
        """

        if self._transcript is not None:
            self._record_action(EventName.PRESS, locator, key=key_masked(locator, key))

        self._narrator.press(locator, key)

    def reveal(
        self,
        locator: Locator,
        *,
        headline: str,
        body: str = '',
        step: str = '',
        label: str = '',
        shot: str = '',
    ) -> None:
        """
        A method that shows the viewer an element, once it is on the page.

        The element is waited for before anything is said about it, so a caption
        never describes something the viewer cannot see.

        :param locator: The locator for the element to show.
        :param headline: The narration headline.
        :param body: The narration body shown under the headline.
        :param step: The step label the narration carries.
        :param label: The caption shown beside the element.
        :param shot: The screenshot name to capture, or an empty string to
            capture nothing.
        :raises AssertionError: If the element never appears.
        """

        expect(locator).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        self.narrate(headline, step=step, body=body)

        self.spotlight(locator, label=label)

        if shot:
            self.screenshot(shot)

    def screenshot(self, name: str) -> None:
        """
        A method that captures the page, if the run takes screenshots.

        :param name: The label for the shot.
        """

        path = self._narrator.screenshot(name)

        if path is not None:
            self._record(EventName.SCREENSHOT, {'name': name, 'file': path.name})

    def select(self, locator: Locator, option_label: str) -> None:
        """
        A method that picks an option from a select element by its label.

        :param locator: The locator for the select element.
        :param option_label: The visible text of the option to pick.
        """

        self._record_action(EventName.SELECT, locator, option=option_label)
        self._narrator.select(locator, option_label)

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        """
        A method that drags a slider handle to the end of its track.

        :param track: The locator for the slider track.
        :param thumb: The locator for the slider handle.
        """

        self._record_action(EventName.SLIDE, thumb)
        self._narrator.slide(track=track, thumb=thumb)

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        hold_ms: int | None = None,
    ) -> None:
        """
        A method that highlights an element and dims the rest of the page.

        The event is recorded only when the spotlight carries a label, because an
        unlabeled highlight leaves nothing for the walkthrough or the voiceover to say.

        :param locator: The locator for the element to highlight.
        :param label: The caption shown beside the element.
        :param dim: Whether the rest of the page is dimmed.
        :param scroll: Whether the element is scrolled into view first.
        :param hold_ms: The time the highlight is held, or None for the default.
        :raises ValueError: If the duration is not positive, or passes the hold limit.
        """

        _hold_ms_validate(hold_ms)

        if label:
            self._record(EventName.SPOTLIGHT, {'label': label})

        self._narrator.spotlight(locator, label=label, dim=dim, scroll=scroll, hold_ms=hold_ms)

    def switch_page(self, page: Page) -> None:
        """
        A method that moves the demo onto a different page.

        :param page: The page the demo drives from here on.
        """

        self._page_prepared(page)

        self.page = page

        self._narrator.switch_page(page)

        if self._renderer is not None:
            self._renderer.switch_page(page)

    def title(
        self,
        text: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        hold_ms: int | None = None,
    ) -> None:
        """
        A method that shows a full-screen title card.

        :param text: The heading for the card.
        :param kicker: The line above the heading.
        :param subtitle: The line below the heading.
        :param hold_ms: The time the card is held on screen, or None for the default.
        :raises ValueError: If the duration is not positive, or passes the hold limit.
        """

        _hold_ms_validate(hold_ms)

        detail = {
            'title': text,
            'kicker': kicker,
            'subtitle': subtitle,
        }

        self._record(EventName.TITLE, detail)

        hold_ms_resolved = self._hold_ms_for(hold_ms, detail)

        self._narrator.title(text, kicker=kicker, subtitle=subtitle, hold_ms=hold_ms_resolved)

    def uncheck(self, locator: Locator) -> None:
        """
        A method that clears a checkbox.

        :param locator: The locator for the checkbox.
        """

        self._record_action(EventName.UNCHECK, locator)
        self._narrator.uncheck(locator)

    def wait(self, hold_ms: int) -> None:
        """
        A method that holds the demo for a duration.

        :param hold_ms: The time to hold for.
        :raises ValueError: If the duration is not positive, or passes the hold limit.
        """

        _hold_ms_validate(hold_ms)

        self._narrator.wait(hold_ms)

    def wait_until(
        self,
        predicate: Callable[[], bool],
        *,
        attempt_count_max: int = barriers.WAIT_ATTEMPT_COUNT_MAX_DEFAULT,
        description: str = '',
        interval_ms: int = barriers.WAIT_INTERVAL_MS_DEFAULT,
    ) -> None:
        """
        A method that polls a condition until it holds.

        The holds between polls go through the narrator, so a rendered demo polls on
        the frames it draws rather than on the wall clock.

        :param predicate: The condition polled between holds.
        :param attempt_count_max: The number of times the condition is polled.
        :param description: The name of the condition, used in the failure message.
        :param interval_ms: The time held between polls.
        :raises ValueError: If the attempt count or the interval is not positive.
        :raises BarrierError: If the condition never holds.
        """

        barriers.wait_until(
            self._narrator.wait,
            predicate,
            attempt_count_max=attempt_count_max,
            description=description,
            interval_ms=interval_ms,
        )


def locator_label(locator: Locator) -> str:
    """
    A function that reads the label a viewer would use for an element.

    The label is read through the page rather than from the locator, because a
    locator names how the element was found and a walkthrough has to name what the
    element says.

    :param locator: The locator for the element.
    :return: The label of the element, or an empty string if it has none.
    """

    label = ''

    with contextlib.suppress(PlaywrightError):
        label = locator.evaluate(LOCATOR_LABEL_SCRIPT, timeout=LOCATOR_LABEL_TIMEOUT_MS)

    return str(label or '')
