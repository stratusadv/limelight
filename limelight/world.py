from __future__ import annotations

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing_extensions import TypeVar


    T = TypeVar('T')


class WorldBase:
    def _claim(self, registry: Mapping[str, object], name: str, kind: str) -> None:
        if name in registry:
            message = f'{kind} already seeded: {name}'
            raise ValueError(message)

    def _require(self, registry: Mapping[str, T], name: str, kind: str) -> T:
        if name not in registry:
            message = f'{kind} not seeded: {name}'
            raise KeyError(message)

        return registry[name]
