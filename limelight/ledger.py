from __future__ import annotations

from decimal import Decimal
from typing_extensions import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing_extensions import Callable, Self


DIRECTION_DOWN = 'down'
DIRECTION_FLAT = 'flat'
DIRECTION_UP = 'up'

DELTA_SIGNS = {
    DIRECTION_DOWN: '-',
    DIRECTION_FLAT: '',
    DIRECTION_UP: '+',
}

IMPROVES_DIRECTIONS = (DIRECTION_DOWN, DIRECTION_UP)

SENTIMENT_BAD = 'bad'
SENTIMENT_FLAT = 'flat'
SENTIMENT_GOOD = 'good'


def _direction(delta: float) -> str:
    if delta > 0:
        return DIRECTION_UP

    if delta < 0:
        return DIRECTION_DOWN

    return DIRECTION_FLAT


def _sentiment(delta: float, improves: str) -> str:
    direction = _direction(delta)

    if direction == DIRECTION_FLAT:
        return SENTIMENT_FLAT

    if direction == improves:
        return SENTIMENT_GOOD

    return SENTIMENT_BAD


def _format_number(value: float) -> str:
    number = Decimal(str(value))

    if number == number.to_integral_value():
        return f'{int(number):,}'

    return f'{number:,.2f}'


class Ledger:
    def __init__(self) -> None:
        self._metrics: dict[str, LedgerMetric] = {}

    @staticmethod
    def _delta_label(delta: float, unit: str) -> str:
        sign = DELTA_SIGNS[_direction(delta)]
        magnitude = _format_number(abs(delta))

        return f'{sign}{magnitude} {unit}'.strip()

    def _values_validate(self, values: Mapping[str, float], kind: str) -> None:
        labels_missing = sorted(set(self._metrics) - set(values))

        if labels_missing:
            labels = ', '.join(labels_missing)

            message = f'{kind} values are missing tracked metrics: {labels}'
            raise KeyError(message)

    @staticmethod
    def _value_label(value: float, unit: str) -> str:
        return f'{_format_number(value)} {unit}'.strip()

    def rows(self, before: Mapping[str, float], after: Mapping[str, float] | None = None) -> list[LedgerRow]:
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
        return {label: float(metric.probe()) for label, metric in self._metrics.items()}

    def track(
        self,
        label: str,
        probe: Callable[[], float],
        *,
        improves: str = DIRECTION_UP,
        unit: str = '',
    ) -> Self:
        if improves not in IMPROVES_DIRECTIONS:
            options = ', '.join(IMPROVES_DIRECTIONS)

            message = f'improves must be one of: {options} (got "{improves}")'
            raise ValueError(message)

        self._metrics[label] = LedgerMetric(probe, improves=improves, unit=unit)

        return self


class LedgerMetric:
    def __init__(self, probe: Callable[[], float], *, improves: str = DIRECTION_UP, unit: str) -> None:
        self.improves = improves
        self.probe = probe
        self.unit = unit


class LedgerRow(TypedDict):
    after: str
    before: str
    delta: str
    direction: str
    label: str
    sentiment: str
