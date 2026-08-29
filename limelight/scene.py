from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

    from limelight.demo import Demo


class Scene:
    """
    A page object for a single screen of a demo.

    This class pairs a route with the assertions that prove the screen has
    loaded. A subclass sets the route and overrides expect_ready().
    """

    route = ''

    def __init__(self, demo: Demo) -> None:
        """
        The constructor for the Scene class.

        :param demo: The demo that drives the browser for this scene.
        """

        self.demo = demo

    def expect_ready(self) -> None:
        """
        A method that waits until the scene has finished loading.

        The base implementation does nothing, so a scene that needs to settle
        before the next step overrides this with its own assertions.
        """

    def open(self, **url_kwargs: object) -> Self:
        """
        A method that navigates to the scene route and waits for it to be ready.

        :param url_kwargs: The arguments used to reverse the route into a URL.
        :return: The scene itself, so calls can be chained.
        :raises ValueError: If the route has not been set on the subclass.
        """

        if not self.route:
            message = f'{type(self).__name__}.route must be set before open()'
            raise ValueError(message)

        self.demo.goto(self.route, **url_kwargs)
        self.expect_ready()

        return self
