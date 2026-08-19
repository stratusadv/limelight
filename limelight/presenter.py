from __future__ import annotations

import contextlib

from typing_extensions import TYPE_CHECKING, Protocol, runtime_checkable

from playwright.sync_api import Error as PlaywrightError

from limelight.camera import Camera
from limelight.gestures import slide_to_end
from limelight.overlay import BEAT_MS_DEFAULT, Overlay
from limelight.transcript import Transcript

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from playwright.sync_api import Locator, Page

    from limelight.config import DemoConfig
    from limelight.ledger import LedgerRow
    from limelight.theme import Theme


LOCATOR_LABEL_SCRIPT = (
    "element => (element.innerText || element.value || element.getAttribute('aria-label')"
    " || element.getAttribute('placeholder') || '').trim().split('\\n')[0].slice(0, 80)"
)

LOCATOR_LABEL_TIMEOUT_MS = 2000

TRANSCRIPT_FILE_NAME = 'transcript.json'


@runtime_checkable
class Presenter(Protocol):
    def beat(self, ms: int = BEAT_MS_DEFAULT) -> None: ...

    def check(self, locator: Locator) -> None: ...

    def clear(self) -> None: ...

    def clear_spotlight(self) -> None: ...

    def click(self, locator: Locator, *, force: bool = False) -> None: ...

    def delta_card(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None: ...

    def fill(self, locator: Locator, value: str) -> None: ...

    def hold(self) -> None: ...

    def hover(self, locator: Locator) -> None: ...

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        tag: str = '',
        kind: str = '',
        ms: int | None = None,
    ) -> None: ...

    def press(self, locator: Locator, key: str) -> None: ...

    def select(self, locator: Locator, option_label: str) -> None: ...

    def shot(self, name: str) -> None: ...

    def slide(self, *, track: Locator, thumb: Locator) -> None: ...

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None: ...

    def title_card(
        self,
        title: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None: ...

    def uncheck(self, locator: Locator) -> None: ...

    def use_page(self, page: Page) -> None: ...


class PresenterNarrated:
    def __init__(self, *, camera: Camera, overlay: Overlay, transcript: Transcript | None = None) -> None:
        self._camera = camera
        self._overlay = overlay
        self._transcript = transcript

    def _locator_label(self, locator: Locator) -> str:
        label = ''

        with contextlib.suppress(PlaywrightError):
            label = locator.evaluate(LOCATOR_LABEL_SCRIPT, timeout=LOCATOR_LABEL_TIMEOUT_MS)

        return str(label or '')

    def _record(self, event: str, detail: Mapping[str, object]) -> None:
        if self._transcript is not None:
            self._transcript.record(event, detail)

    def beat(self, ms: int = BEAT_MS_DEFAULT) -> None:
        self._overlay.beat(ms)

    def check(self, locator: Locator) -> None:
        detail = {'target': self._locator_label(locator)}

        self._record('check', detail)
        self._overlay.check(locator)

    def clear(self) -> None:
        self._overlay.clear()

    def clear_spotlight(self) -> None:
        self._overlay.clear_spotlight()

    def click(self, locator: Locator, *, force: bool = False) -> None:
        detail = {'target': self._locator_label(locator)}

        self._record('click', detail)
        self._overlay.click(locator, force=force)

    def delta_card(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        detail = {
            'title': title,
            'kicker': kicker,
            'subtitle': subtitle,
            'rows': list(rows),
        }

        self._record('delta_card', detail)
        self._overlay.delta_card(title, rows, kicker=kicker, subtitle=subtitle, ms=ms)

    def fill(self, locator: Locator, value: str) -> None:
        detail = {'target': self._locator_label(locator), 'value': value}

        self._record('fill', detail)
        self._overlay.fill(locator, value)

    def hold(self) -> None:
        self._overlay.hold()

    def hover(self, locator: Locator) -> None:
        detail = {'target': self._locator_label(locator)}

        self._record('hover', detail)
        self._overlay.hover(locator)

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        tag: str = '',
        kind: str = '',
        ms: int | None = None,
    ) -> None:
        detail = {
            'title': title,
            'body': body,
            'step': step,
            'tag': tag,
            'kind': kind,
        }

        self._record('narrate', detail)
        self._overlay.narrate(title, body=body, step=step, tag=tag, kind=kind, ms=ms)

    def press(self, locator: Locator, key: str) -> None:
        detail = {'target': self._locator_label(locator), 'key': key}

        self._record('press', detail)
        self._overlay.press(locator, key)

    def select(self, locator: Locator, option_label: str) -> None:
        detail = {'target': self._locator_label(locator), 'option': option_label}

        self._record('select', detail)
        self._overlay.select(locator, option_label)

    def shot(self, name: str) -> None:
        self._overlay.control_hide()
        self._overlay.cursor_hide()

        path = self._camera.shot(name)

        self._overlay.control_show()

        if path is not None:
            detail = {'name': name, 'file': path.name}

            self._record('shot', detail)

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        detail = {'target': self._locator_label(thumb)}

        self._record('slide', detail)
        self._overlay.slide(track=track, thumb=thumb)

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None:
        if label:
            detail = {'label': label}

            self._record('spotlight', detail)

        self._overlay.spotlight(locator, label=label, dim=dim, scroll=scroll, ms=ms)

    def title_card(
        self,
        title: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        detail = {
            'title': title,
            'kicker': kicker,
            'subtitle': subtitle,
        }

        self._record('title_card', detail)
        self._overlay.title_card(title, kicker=kicker, subtitle=subtitle, ms=ms)

    def uncheck(self, locator: Locator) -> None:
        detail = {'target': self._locator_label(locator)}

        self._record('uncheck', detail)
        self._overlay.uncheck(locator)

    def use_page(self, page: Page) -> None:
        self._camera.use_page(page)
        self._overlay.use_page(page)


class PresenterSilent:
    def beat(self, ms: int = BEAT_MS_DEFAULT) -> None:
        pass

    def check(self, locator: Locator) -> None:
        locator.check()

    def clear(self) -> None:
        pass

    def clear_spotlight(self) -> None:
        pass

    def click(self, locator: Locator, *, force: bool = False) -> None:
        locator.click(force=force)

    def delta_card(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        pass

    def fill(self, locator: Locator, value: str) -> None:
        locator.fill(value)

    def hold(self) -> None:
        pass

    def hover(self, locator: Locator) -> None:
        locator.hover()

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        tag: str = '',
        kind: str = '',
        ms: int | None = None,
    ) -> None:
        pass

    def press(self, locator: Locator, key: str) -> None:
        locator.press(key)

    def select(self, locator: Locator, option_label: str) -> None:
        locator.select_option(label=option_label)

    def shot(self, name: str) -> None:
        pass

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        slide_to_end(track.page, track=track, thumb=thumb)

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None:
        pass

    def title_card(
        self,
        title: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        pass

    def uncheck(self, locator: Locator) -> None:
        locator.uncheck()

    def use_page(self, page: Page) -> None:
        pass


def presenter_build(
    page: Page,
    config: DemoConfig,
    *,
    shot_directory: Path,
    theme: Theme | None = None,
) -> Presenter:
    if config.narrated:
        camera = Camera(page, shot_directory, enabled=config.shots)
        transcript = Transcript(shot_directory / TRANSCRIPT_FILE_NAME)

        overlay = Overlay(
            page,
            config.timing,
            controls=not config.video,
            speed_factor=config.speed_factor,
            step_mode=config.present,
            theme=theme,
        )

        return PresenterNarrated(camera=camera, overlay=overlay, transcript=transcript)

    return PresenterSilent()
