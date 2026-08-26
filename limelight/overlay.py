from __future__ import annotations

import contextlib
import json
import time

from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from limelight.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Mapping

    from playwright.sync_api import FloatRect, Locator, Page

    from limelight.frames import FrameClock
    from limelight.ledger import LedgerRow
    from limelight.timing import DemoTiming


BEAT_MS_DEFAULT = 1100
CURSOR_MOVE_MS = 500
CURSOR_PULSE_MS = 350
INPUT_DRIVE_SLACK_MS = 5000
INPUT_TYPES_UNTYPEABLE = ('color', 'date', 'datetime-local', 'month', 'range', 'time', 'week')
INPUT_TYPE_SCRIPT = "element => element.tagName === 'INPUT' ? (element.type || 'text').toLowerCase() : ''"
INPUT_TYPE_TIMEOUT_MS = 2000
OVERLAY_JAVASCRIPT = files('limelight').joinpath('assets/overlay.js').read_text(encoding='utf-8')
SETTLE_MS_MAX = 2000
SLIDE_CHUNK_COUNT = 8
SLIDE_MOUSE_STEP_COUNT = 3
SLIDE_MS = 700
SPEED_FACTOR_LIVE_MAX = 1000.0
SPEED_FACTOR_LIVE_MIN = 0.1
SPOT_BOX_POLL_MS = 60
SPOT_BOX_SAMPLE_COUNT_MAX = 25
SPOT_BOX_TIMEOUT_MS = 4000
SPOT_SCROLL_SETTLE_MS = 250
SPOT_SCROLL_TIMEOUT_MS = 4000
TITLE_FADE_MS = 450
TYPE_CHAR_MS = 55
WAIT_OVERHEAD_MS_MIN = 1.0
WAIT_PAUSED_MS_MAX = 3_600_000
WAIT_SLICE_COUNT_MAX = 100_000
WAIT_SLICE_MS = 100


@dataclass(frozen=True)
class ControlState:
    paused: bool
    skip: bool
    speed_factor: float


class Overlay:
    def __init__(
        self,
        page: Page,
        timing: DemoTiming,
        *,
        clock: FrameClock | None = None,
        controls: bool = False,
        speed_factor: float = 1.0,
        step_mode: bool = False,
        theme: Theme | None = None,
    ) -> None:
        if step_mode and not controls:
            message = 'step_mode requires controls; there is no other way to advance'
            raise ValueError(message)

        if speed_factor <= 0:
            message = f'speed_factor must be positive: {speed_factor}'
            raise ValueError(message)

        self._clock = clock
        self._controls = controls
        self._page = page
        self._speed_factor = self._speed_factor_clamped(speed_factor)
        self._step_mode = step_mode
        self._theme = theme if theme is not None else Theme()
        self._timing = timing

        self._install(page)

    def _box_settled(self, locator: Locator) -> FloatRect | None:
        box_previous = None

        for _ in range(SPOT_BOX_SAMPLE_COUNT_MAX):
            try:
                box = locator.bounding_box(timeout=SPOT_BOX_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                return None

            if box is not None and box == box_previous:
                return box

            box_previous = box

            self._page.wait_for_timeout(SPOT_BOX_POLL_MS)

        return box_previous

    def _call(self, function_name: str, argument: Mapping[str, object] | None = None) -> object:
        expression = f'(argument) => window.__limelight && window.__limelight.{function_name}(argument)'

        return self._page.evaluate(expression, argument)

    def _control_state(self) -> ControlState | None:
        return self._control_state_read('controlRead')

    def _control_state_peek(self) -> ControlState | None:
        return self._control_state_read('controlPeek')

    def _control_state_read(self, function_name: str) -> ControlState | None:
        expression = f'() => window.__limelight ? window.__limelight.{function_name}() : null'
        state = self._page.evaluate(expression)

        if state is None:
            return None

        return ControlState(
            paused=bool(state['paused']),
            skip=bool(state['skip']),
            speed_factor=float(state['speedFactor']),
        )

    def _cursor_glide(self, locator: Locator) -> None:
        box = self._box_settled(locator)

        if box is None:
            return

        reference_ms = int(self._timing.scale(CURSOR_MOVE_MS) / self._live_speed_factor())

        argument = {
            'x': box['x'] + box['width'] / 2,
            'y': box['y'] + box['height'] / 2,
            'ms': reference_ms,
        }

        result = self._call('cursorMove', argument)
        move_ms = float(reference_ms)

        if isinstance(result, int | float) and not isinstance(result, bool):
            move_ms = float(result)

        self._sleep(move_ms)

    def _cursor_pulse(self) -> None:
        pulse_ms = int(self._timing.scale(CURSOR_PULSE_MS) / self._live_speed_factor())

        self._call('cursorPulse')
        self._sleep(pulse_ms)

    def _ensure(self) -> None:
        argument = self._settings()

        self._page.wait_for_selector('body', state='attached')
        self._page.evaluate(OVERLAY_JAVASCRIPT, argument)

    def _install(self, page: Page) -> None:
        argument = json.dumps(self._settings())

        script = (
            'document.addEventListener("DOMContentLoaded", () => {'
            f'({OVERLAY_JAVASCRIPT})({argument});'
            '});'
        )

        page.add_init_script(script)

    def _live_speed_factor(self) -> float:
        if not self._controls:
            return self._speed_factor

        state = self._control_state_peek()

        if state is None:
            return self._speed_factor

        return self._speed_factor_clamped(state.speed_factor)

    def _scroll(self, locator: Locator) -> None:
        with contextlib.suppress(PlaywrightTimeoutError):
            locator.scroll_into_view_if_needed(timeout=SPOT_SCROLL_TIMEOUT_MS)

        self._wait(SPOT_SCROLL_SETTLE_MS, gated=False)

    def _input_drive_begin(self, ms: float) -> None:
        argument = {'ms': ms + INPUT_DRIVE_SLACK_MS}

        self._call('inputDriveBegin', argument)

    def _input_drive_end(self) -> None:
        self._call('inputDriveEnd')

    def _settings(self) -> dict[str, object]:
        return {
            'theme': self._theme.payload(),
            'controls': self._controls,
            'speedFactor': self._speed_factor,
            'stepMode': self._step_mode,
        }

    def _settle(self) -> None:
        with contextlib.suppress(PlaywrightError):
            self._call('settle', {'ms': SETTLE_MS_MAX})

    def _sleep(self, ms: float) -> None:
        if self._clock is not None:
            self._clock.wait_ms(ms)

            return

        self._page.wait_for_timeout(ms)

    def _speed_factor_clamped(self, speed_factor: float) -> float:
        if speed_factor < SPEED_FACTOR_LIVE_MIN:
            return SPEED_FACTOR_LIVE_MIN

        if speed_factor > SPEED_FACTOR_LIVE_MAX:
            return SPEED_FACTOR_LIVE_MAX

        return speed_factor

    def _overhead_ms(self, started: float) -> float:
        elapsed_ms = (time.monotonic() - started) * 1000

        if elapsed_ms < WAIT_OVERHEAD_MS_MIN:
            return 0.0

        return elapsed_ms

    def _spent_ms(self, started: float, floor_ms: float) -> float:
        elapsed_ms = (time.monotonic() - started) * 1000

        return max(floor_ms, elapsed_ms)

    def _step_ms(self, ms: int | None) -> int:
        if ms is not None:
            return ms

        return self._timing.step_ms

    def _typed_by_frame(self, locator: Locator, value: str, delay_ms: float) -> None:
        for character in value:
            locator.press_sequentially(character)
            self._sleep(delay_ms)

    def _typing_reproduces_value(self, locator: Locator) -> bool:
        input_type = ''

        with contextlib.suppress(PlaywrightError):
            input_type = str(locator.evaluate(INPUT_TYPE_SCRIPT, timeout=INPUT_TYPE_TIMEOUT_MS) or '')

        return input_type not in INPUT_TYPES_UNTYPEABLE

    def _type_delay_ms(self) -> float:
        return TYPE_CHAR_MS * self._timing.scale_factor / self._live_speed_factor()

    def _wait(self, ms: int, *, gated: bool = True) -> None:
        if self._step_mode and gated:
            self._wait_step()

            return

        remaining_ms = float(self._timing.scale(ms))

        if not self._controls:
            self._sleep(remaining_ms / self._live_speed_factor())

            return

        ensure_started = time.monotonic()

        self._ensure()

        remaining_ms -= self._overhead_ms(ensure_started)

        paused_ms_total = 0.0

        for _ in range(WAIT_SLICE_COUNT_MAX):
            if remaining_ms <= 0:
                return

            started = time.monotonic()
            state = self._control_state() if gated else self._control_state_peek()

            if state is None:
                self._page.wait_for_timeout(remaining_ms)

                return

            if state.skip:
                return

            if state.paused:
                self._page.wait_for_timeout(WAIT_SLICE_MS)

                paused_ms_total += self._spent_ms(started, WAIT_SLICE_MS)

                if paused_ms_total > WAIT_PAUSED_MS_MAX:
                    message = f'demo paused longer than {WAIT_PAUSED_MS_MAX}ms; aborting'
                    raise TimeoutError(message)

                continue

            speed_factor = self._speed_factor_clamped(state.speed_factor)
            state_read_ms = self._overhead_ms(started)
            slice_ms = min(float(WAIT_SLICE_MS), max(0.0, remaining_ms / speed_factor - state_read_ms))

            self._page.wait_for_timeout(slice_ms)

            remaining_ms -= self._spent_ms(started, slice_ms) * speed_factor

        message = f'wait exceeded {WAIT_SLICE_COUNT_MAX} slices with {remaining_ms}ms left; aborting'
        raise TimeoutError(message)

    def _wait_step(self) -> None:
        self._ensure()

        waited_ms_total = 0

        for _ in range(WAIT_SLICE_COUNT_MAX):
            state = self._control_state()

            if state is None:
                return

            if state.skip:
                return

            waited_ms_total += WAIT_SLICE_MS

            if waited_ms_total > WAIT_PAUSED_MS_MAX:
                message = f'step wait exceeded {WAIT_PAUSED_MS_MAX}ms without advancing; aborting'
                raise TimeoutError(message)

            self._page.wait_for_timeout(WAIT_SLICE_MS)

        message = f'step wait exceeded {WAIT_SLICE_COUNT_MAX} slices without advancing; aborting'
        raise TimeoutError(message)

    def beat(self, ms: int = BEAT_MS_DEFAULT) -> None:
        self._wait(ms)

    def check(self, locator: Locator) -> None:
        self._ensure()
        self._settle()
        self._scroll(locator)
        self._cursor_glide(locator)
        self._cursor_pulse()

        locator.check()

    def clear(self) -> None:
        self._call('spotClear')
        self._call('captionHide')
        self._call('backdropHide')

    def clear_spotlight(self) -> None:
        self._call('spotClear')

    def click(self, locator: Locator, *, force: bool = False) -> None:
        self._ensure()
        self._settle()
        self._scroll(locator)
        self._cursor_glide(locator)
        self._cursor_pulse()

        locator.click(force=force)

    def control_hide(self) -> None:
        self._call('controlHide')

    def control_show(self) -> None:
        self._call('controlShow')

    def cursor_hide(self) -> None:
        self._call('cursorHide')

    def delta_card(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self._ensure()
        self._call('spotClear')
        self._call('captionRemove')
        self._call('backdropRemove')

        argument = {'title': title, 'kicker': kicker, 'subtitle': subtitle, 'rows': rows}
        self._call('delta', argument)

        self._wait(self._step_ms(ms))

        self._call('deltaHide')
        self._wait(TITLE_FADE_MS, gated=False)
        self._call('deltaRemove')

    def fill(self, locator: Locator, value: str) -> None:
        self.click(locator)

        if not self._typing_reproduces_value(locator):
            locator.fill(value)

            return

        delay_ms = self._type_delay_ms()

        self._input_drive_begin(len(value) * delay_ms)
        self._call('keyHudEnable')

        locator.fill('')

        if self._clock is None:
            locator.press_sequentially(value, delay=delay_ms)
        else:
            self._typed_by_frame(locator, value, delay_ms)

        self._call('keyHudDisable')
        self._input_drive_end()

    def hold(self) -> None:
        self._wait(self._timing.step_ms)

    def hover(self, locator: Locator) -> None:
        self._ensure()
        self._settle()
        self._scroll(locator)
        self._cursor_glide(locator)

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
        self._ensure()
        self._call('spotClear')
        self._call('backdropShow')

        argument = {'title': title, 'body': body, 'step': step, 'tag': tag, 'kind': kind}
        self._call('caption', argument)

        self._wait(self._step_ms(ms))

        self._call('captionRemove')
        self._call('backdropRemove')

    def press(self, locator: Locator, key: str) -> None:
        self._ensure()
        self._settle()

        argument = {'text': key}
        self._call('keyFlash', argument)
        self._input_drive_begin(0)

        locator.press(key)

        self._input_drive_end()

    def select(self, locator: Locator, option_label: str) -> None:
        self._ensure()
        self._settle()
        self._scroll(locator)
        self._cursor_glide(locator)
        self._cursor_pulse()

        locator.select_option(label=option_label)

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        self._ensure()
        self._settle()
        self._scroll(thumb)
        self._cursor_glide(thumb)
        self._cursor_pulse()

        track_box = track.bounding_box()
        thumb_box = thumb.bounding_box()

        if track_box is None:
            message = 'track has no bounding box; is it visible?'
            raise ValueError(message)

        if thumb_box is None:
            message = 'thumb has no bounding box; is it visible?'
            raise ValueError(message)

        x_start = thumb_box['x'] + thumb_box['width'] / 2
        x_end = track_box['x'] + track_box['width']
        y_center = thumb_box['y'] + thumb_box['height'] / 2
        chunk_ms = max(1, int(self._timing.scale(SLIDE_MS) / self._live_speed_factor()) // SLIDE_CHUNK_COUNT)

        mouse = self._page.mouse

        mouse.move(x_start, y_center)
        mouse.down()

        for chunk_index in range(1, SLIDE_CHUNK_COUNT + 1):
            x_chunk = x_start + (x_end - x_start) * chunk_index / SLIDE_CHUNK_COUNT
            argument = {'x': x_chunk, 'y': y_center, 'ms': chunk_ms, 'direct': True}

            self._call('cursorMove', argument)
            mouse.move(x_chunk, y_center, steps=SLIDE_MOUSE_STEP_COUNT)
            self._sleep(chunk_ms)

        mouse.up()

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None:
        self._ensure()
        self._call('captionRemove')
        self._call('backdropRemove')

        if scroll:
            self._scroll(locator)

        box = self._box_settled(locator)

        if box is not None:
            argument = {'box': box, 'label': label, 'dim': dim}
            self._call('spot', argument)

        self._wait(self._step_ms(ms))

    def title_card(
        self,
        title: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self._ensure()
        self._call('spotClear')
        self._call('captionRemove')
        self._call('backdropRemove')

        argument = {'kicker': kicker, 'title': title, 'subtitle': subtitle}
        self._call('title', argument)

        self._wait(self._step_ms(ms))

        self._call('titleHide')
        self._wait(TITLE_FADE_MS, gated=False)
        self._call('titleRemove')

    def uncheck(self, locator: Locator) -> None:
        self._ensure()
        self._scroll(locator)
        self._cursor_glide(locator)
        self._cursor_pulse()

        locator.uncheck()

    def use_page(self, page: Page) -> None:
        self._install(page)

        self._page = page
