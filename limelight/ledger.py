from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Self


class Direction(StrEnum):
    """An enumeration of the ways a metric can move between two readings."""

    DOWN = 'down'
    FLAT = 'flat'
    UP = 'up'


class Sentiment(StrEnum):
    """An enumeration of how a movement reads to a viewer."""

    BAD = 'bad'
    FLAT = 'flat'
    GOOD = 'good'


DELTA_SIGNS = {
    Direction.DOWN: '-',
    Direction.FLAT: '',
    Direction.UP: '+',
}

IMPROVES_DIRECTIONS = (Direction.DOWN, Direction.UP)


def _direction(delta: float) -> Direction:
    """
    A function that classifies the sign of a change.

    :param delta: The change between the before and after readings.
    :return: The direction the metric moved in.
    """

    if delta > 0:
        return Direction.UP

    if delta < 0:
        return Direction.DOWN

    return Direction.FLAT


def _format_number(value: float) -> str:
    """
    A function that formats a number for a ledger cell.

    The value goes through Decimal because a float carries the binary rounding of
    its own representation, so a whole number such as 3.0 has to be recognized as
    whole before it can be printed without a decimal part.

    :param value: The number to format.
    :return: The number with thousands separators, and two decimal places if it is not whole.
    """

    number = Decimal(str(value))

    if number == number.to_integral_value():
        return f'{int(number):,}'

    return f'{number:,.2f}'


def _sentiment(delta: float, improves: Direction) -> Sentiment:
    """
    A function that decides whether a change is good, bad, or neither.

    :param delta: The change between the before and after readings.
    :param improves: The direction that counts as an improvement for this metric.
    :return: The sentiment the change carries.
    """

    direction = _direction(delta)

    if direction is Direction.FLAT:
        return Sentiment.FLAT

    if direction is improves:
        return Sentiment.GOOD

    return Sentiment.BAD


class Ledger:
    """
    A recorder for the metrics a demo compares before and after a workflow.

    This class tracks a metric by name along with the probe that reads it and the
    direction that counts as an improvement, then renders the readings as rows the
    overlay can draw.
    """

    def __init__(self) -> None:
        """The constructor for the Ledger class."""

        self._metrics: dict[str, LedgerMetric] = {}

    @staticmethod
    def _delta_label(delta: float, unit: str) -> str:
        """
        A method that formats a change as a signed, united string.

        :param delta: The change between the before and after readings.
        :param unit: The unit the metric is measured in.
        :return: The change with its sign and unit.
        """

        sign = DELTA_SIGNS[_direction(delta)]
        magnitude = _format_number(abs(delta))

        return f'{sign}{magnitude} {unit}'.strip()

    def _values_validate(self, values: Mapping[str, float], kind: str) -> None:
        """
        A method that rejects a reading that omits a tracked metric.

        :param values: The readings keyed by metric label.
        :param kind: The name of the reading, used in the error message.
        :raises KeyError: If any tracked metric has no reading.
        """

        labels_missing = sorted(set(self._metrics) - set(values))

        if labels_missing:
            labels = ', '.join(labels_missing)

            message = f'{kind} values are missing tracked metrics: {labels}'
            raise KeyError(message)

    @staticmethod
    def _value_label(value: float, unit: str) -> str:
        """
        A method that formats a reading as a united string.

        :param value: The reading to format.
        :param unit: The unit the metric is measured in.
        :return: The reading with its unit.
        """

        return f'{_format_number(value)} {unit}'.strip()

    def rows(
        self,
        before: Mapping[str, float],
        *,
        after: Mapping[str, float] | None = None,
    ) -> list[LedgerRow]:
        """
        A method that renders the tracked metrics as before and after rows.

        :param before: The readings taken before the workflow.
        :param after: The readings taken after the workflow, or None to probe them now.
        :return: One row per tracked metric, in the order the metrics were tracked.
        :raises KeyError: If either reading omits a tracked metric.
        """

        after_values = after if after is not None else self.snapshot()

        self._values_validate(before, 'before')
        self._values_validate(after_values, 'after')

        rows: list[LedgerRow] = []

        for label, metric in self._metrics.items():
            before_value = before[label]
            after_value = after_values[label]
            delta = after_value - before_value

            row: LedgerRow = {
                'label': label,
                'before': self._value_label(before_value, metric.unit),
                'after': self._value_label(after_value, metric.unit),
                'delta': self._delta_label(delta, metric.unit),
                'direction': _direction(delta),
                'sentiment': _sentiment(delta, metric.improves),
            }

            rows.append(row)

        return rows

    def snapshot(self) -> dict[str, float]:
        """
        A method that reads every tracked metric through its probe.

        :return: The current reading of each metric, keyed by label.
        """

        return {label: float(metric.probe()) for label, metric in self._metrics.items()}

    def track(
        self,
        label: str,
        probe: Callable[[], float],
        *,
        improves: Direction = Direction.UP,
        unit: str = '',
    ) -> Self:
        """
        A method that registers a metric and the probe that reads it.

        :param label: The name the metric is shown under.
        :param probe: The callable that reads the current value.
        :param improves: The direction that counts as an improvement.
        :param unit: The unit the metric is measured in.
        :return: The ledger itself, so calls can be chained.
        :raises ValueError: If the improving direction is flat.
        """

        if improves not in IMPROVES_DIRECTIONS:
            options = ', '.join(IMPROVES_DIRECTIONS)

            message = f'improves must be one of: {options} (got "{improves}")'
            raise ValueError(message)

        self._metrics[label] = LedgerMetric(improves=Direction(improves), probe=probe, unit=unit)

        return self


@dataclass(frozen=True)
class LedgerMetric:
    """A tracked metric, its probe, and the direction that improves it."""

    improves: Direction
    probe: Callable[[], float]
    unit: str


class LedgerRow(TypedDict):
    """A rendered comparison of one metric before and after a workflow."""

    after: str
    before: str
    delta: str
    direction: Direction
    label: str
    sentiment: Sentiment
