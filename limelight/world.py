from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import TypeVar


    T = TypeVar('T')


class World:
    """
    A registry of the objects a demo has seeded, addressed by name.

    A demo reads better when it names what it is looking at rather than carrying
    a model instance from step to step, so a subclass adds one method per kind
    that seeds an object under a key, and one that reads it back. This class
    supplies the two halves those methods share: a claim that refuses to seed the
    same key twice, and a lookup that names the key it could not find.

    ::

        class DemoWorld(World):
            def __init__(self, user):
                super().__init__(user)

                self._orders = {}

            def add_order(self, key, **field_data):
                self._claim(self._orders, key, 'order')

                self._orders[key] = create_test_order(name=key, **field_data)

                return self

            def order(self, key):
                return self._require(self._orders, key, 'order')
    """

    def __init__(self, user: object) -> None:
        """
        The constructor for the World class.

        :param user: The user the demo is signed in as.
        """

        self.user = user

    @staticmethod
    def _claim(registry: Mapping[str, object], name: str, kind: str) -> None:
        """
        A method that refuses a key the registry already holds.

        :param registry: The registry the key is claimed in.
        :param name: The key being claimed.
        :param kind: The kind of object the registry holds, named in the failure.
        :raises ValueError: If the key is already taken.
        """

        if name in registry:
            message = f'{kind} already seeded: {name}'
            raise ValueError(message)

    @staticmethod
    def _require(registry: Mapping[str, T], name: str, kind: str) -> T:
        """
        A method that reads a key the registry must hold.

        :param registry: The registry the key is read from.
        :param name: The key being read.
        :param kind: The kind of object the registry holds, named in the failure.
        :return: The object seeded under the key.
        :raises KeyError: If the key was never seeded.
        """

        if name not in registry:
            message = f'{kind} not seeded: {name}'
            raise KeyError(message)

        return registry[name]
