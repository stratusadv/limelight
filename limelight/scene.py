from __future__ import annotations

from typing_extensions import TYPE_CHECKING

from limelight.actor import Actor

if TYPE_CHECKING:
    from typing_extensions import Self


class Scene(Actor):
    route = ''

    def expect_ready(self) -> None:
        pass

    def open(self, **url_kwargs: object) -> Self:
        if not self.route:
            message = f'{type(self).__name__}.route must be set before open()'
            raise ValueError(message)

        self._demo.goto(self.route, **url_kwargs)
        self.expect_ready()

        return self
