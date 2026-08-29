from __future__ import annotations

import time

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from limelight.capture.renderer import FrameClock
    from limelight.config import DemoConfig
    from limelight.overlay.bridge import Bridge


SPEED_FACTOR_LIVE_MAX = 1000.0
SPEED_FACTOR_LIVE_MIN = 0.1
WAIT_OVERHEAD_MS_MIN = 1.0
WAIT_PAUSED_MS_MAX = 3_600_000
WAIT_SLICE_COUNT_MAX = 100_000
WAIT_SLICE_MS = 100


def _overhead_ms(started: float) -> float:
    """
    A function that measures how long a control read took.

    A reading under a millisecond is reported as zero, because the resolution of
    the clock is the same order as the measurement and subtracting that noise from
    a wait would drift the timeline.

    :param started: The monotonic timestamp the read began at.
    :return: The elapsed milliseconds, or 0 if the read was faster than the floor.
    """

    elapsed_ms = (time.monotonic() - started) * 1000

    if elapsed_ms < WAIT_OVERHEAD_MS_MIN:
        return 0.0

    return elapsed_ms


def _speed_factor_clamped(speed_factor: float) -> float:
    """
    A function that holds a speed factor inside the supported range.

    :param speed_factor: The requested multiplier.
    :return: The multiplier, clamped to the supported range.
    """

    if speed_factor < SPEED_FACTOR_LIVE_MIN:
        return SPEED_FACTOR_LIVE_MIN

    if speed_factor > SPEED_FACTOR_LIVE_MAX:
        return SPEED_FACTOR_LIVE_MAX

    return speed_factor


def _spent_ms(started: float, *, floor_ms: float) -> float:
    """
    A function that measures a slice of wall time against a floor.

    The floor is the duration the slice asked for, so a timer that returns early
    still advances the timeline by what it was told to wait and the loop cannot
    spin.

    :param started: The monotonic timestamp the slice began at.
    :param floor_ms: The shortest duration the slice may report.
    :return: The elapsed milliseconds, or the floor if less time passed.
    """

    elapsed_ms = (time.monotonic() - started) * 1000

    return max(floor_ms, elapsed_ms)


@dataclass(frozen=True)
class ControlState:
    """A reading of the on-screen control bar."""

    paused: bool
    skip: bool
    speed_factor: float


class Playback:
    """
    A pacer for the waits a demo takes between its steps.

    This class turns a requested duration into real time under the pause, skip, and
    speed controls the viewer drives. A run that renders video is handed a
    frame clock instead, so the waits advance the timeline rather than the wall
    clock.
    """

    def __init__(
        self,
        bridge: Bridge,
        config: DemoConfig,
        *,
        clock: FrameClock | None = None,
    ) -> None:
        """
        The constructor for the Playback class.

        :param bridge: The bridge into the overlay running on the page.
        :param config: The configuration the pacing comes from.
        :param clock: The frame clock a rendered run advances, or None for a live run.
        """

        self._bridge = bridge
        self._clock = clock
        self._controls = config.controls
        self._speed_factor = _speed_factor_clamped(config.speed_factor)
        self._step_mode = config.present
        self._step_ms = config.step_ms

    def _state(self, function_name: str) -> ControlState | None:
        """
        A method that reads the control bar through the overlay.

        :param function_name: The name of the overlay function to read through.
        :return: The state of the controls, or None if the overlay is not installed.
        :raises TypeError: If the control bar reports no speed factor.
        """

        state = self._bridge.read(function_name)

        if state is None:
            return None

        speed_factor = state.get('speedFactor')

        if not isinstance(speed_factor, int | float):
            message = f'the control bar reported no speed factor: {state}'
            raise TypeError(message)

        return ControlState(
            paused=bool(state.get('paused')),
            skip=bool(state.get('skip')),
            speed_factor=float(speed_factor),
        )

    def _wait_gated(self, ms: int, *, gated: bool) -> None:
        """
        A method that waits out a duration under the control bar.

        The wait is broken into slices so a pause, a skip, or a speed change takes
        effect partway through rather than at the end. Each slice subtracts the time it
        actually spent, scaled by the speed in force for that slice, so a viewer who
        speeds up mid-wait shortens only the remainder.

        :param ms: The duration to wait at normal speed.
        :param gated: Whether the wait consumes a skip, rather than only observing one.
        :raises TimeoutError: If the pause outlasts the maximum, or the slices run out.
        """

        remaining_ms = float(ms)
        paused_ms_total = 0.0

        for _ in range(WAIT_SLICE_COUNT_MAX):
            if remaining_ms <= 0:
                return

            started = time.monotonic()
            state = self._state('controlRead') if gated else self._state('controlPeek')

            if state is None:
                self._bridge.page.wait_for_timeout(remaining_ms)

                return

            if state.skip:
                return

            if state.paused:
                self._bridge.page.wait_for_timeout(WAIT_SLICE_MS)

                paused_ms_total += _spent_ms(started, floor_ms=WAIT_SLICE_MS)

                if paused_ms_total > WAIT_PAUSED_MS_MAX:
                    message = f'demo paused longer than {WAIT_PAUSED_MS_MAX}ms; aborting'
                    raise TimeoutError(message)

                continue

            speed_factor = _speed_factor_clamped(state.speed_factor)
            state_read_ms = _overhead_ms(started)
            slice_ms_wanted = max(0.0, remaining_ms / speed_factor - state_read_ms)
            slice_ms = min(float(WAIT_SLICE_MS), slice_ms_wanted)

            self._bridge.page.wait_for_timeout(slice_ms)

            remaining_ms -= _spent_ms(started, floor_ms=slice_ms) * speed_factor

        message = f'wait exceeded {WAIT_SLICE_COUNT_MAX} slices with {remaining_ms}ms left'
        raise TimeoutError(message)

    def _wait_step(self) -> None:
        """
        A method that waits for the viewer to advance the demo by hand.

        :raises TimeoutError: If the viewer never advances within the maximum.
        """

        waited_ms_total = 0

        for _ in range(WAIT_SLICE_COUNT_MAX):
            state = self._state('controlRead')

            if state is None:
                return

            if state.skip:
                return

            waited_ms_total += WAIT_SLICE_MS

            if waited_ms_total > WAIT_PAUSED_MS_MAX:
                message = f'step wait exceeded {WAIT_PAUSED_MS_MAX}ms without advancing; aborting'
                raise TimeoutError(message)

            self._bridge.page.wait_for_timeout(WAIT_SLICE_MS)

        message = f'step wait exceeded {WAIT_SLICE_COUNT_MAX} slices without advancing; aborting'
        raise TimeoutError(message)

    @property
    def frame_paced(self) -> bool:
        """
        A property that reports whether the run is paced by a frame clock.

        :return: True if a frame clock drives the waits, False otherwise.
        """

        return self._clock is not None

    @property
    def speed_factor_live(self) -> float:
        """
        A property that reads the speed the viewer has the demo running at.

        :return: The multiplier in force, falling back to the configured one when
            the controls are absent.
        """

        if not self._controls:
            return self._speed_factor

        state = self._state('controlPeek')

        if state is None:
            return self._speed_factor

        return _speed_factor_clamped(state.speed_factor)

    def sleep(self, ms: float) -> None:
        """
        A method that holds for a duration, on the frame clock or the wall clock.

        :param ms: The duration to hold for.
        """

        if self._clock is not None:
            self._clock.wait_ms(ms)

            return

        self._bridge.page.wait_for_timeout(ms)

    def step_ms_of(self, ms: int | None) -> int:
        """
        A method that resolves a step duration against the configured default.

        :param ms: The duration asked for, or None to use the default.
        :return: The duration the step holds for.
        """

        if ms is not None:
            return ms

        return self._step_ms

    def wait(self, ms: int, *, gated: bool = True) -> None:
        """
        A method that waits out a step.

        :param ms: The duration to wait at normal speed.
        :param gated: Whether the wait consumes a skip, rather than only observing one.
        :raises TimeoutError: If the viewer never advances a stepped or paused demo.
        """

        if self._step_mode:
            if gated:
                self._wait_step()

                return

        if not self._controls:
            self.sleep(ms / self.speed_factor_live)

            return

        self._wait_gated(ms, gated=gated)
