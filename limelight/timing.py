from __future__ import annotations

from dataclasses import dataclass


FAST_MS_MIN = 40
STEP_MS_DEFAULT = 4500


@dataclass(frozen=True)
class DemoTiming:
    step_ms: int = STEP_MS_DEFAULT
    scale_factor: float = 1.0

    def __post_init__(self) -> None:
        if self.step_ms <= 0:
            message = f'step_ms must be positive: {self.step_ms}'
            raise ValueError(message)

        if self.scale_factor <= 0:
            message = f'scale_factor must be positive: {self.scale_factor}'
            raise ValueError(message)

    def scale(self, ms: int) -> int:
        if ms < 0:
            message = f'ms must be non-negative: {ms}'
            raise ValueError(message)

        if self.scale_factor >= 1.0:
            return ms

        return max(FAST_MS_MIN, int(ms * self.scale_factor))
