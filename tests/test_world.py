from __future__ import annotations

import pytest

from limelight.world import World


class DemoWorld(World):
    def __init__(self, user: object) -> None:
        super().__init__(user)

        self._orders: dict[str, str] = {}

    def add_order(self, key: str) -> DemoWorld:
        self._claim(self._orders, key, 'order')

        self._orders[key] = f'order:{key}'

        return self

    def order(self, key: str) -> str:
        return self._require(self._orders, key, 'order')


def test_a_world_carries_the_user_it_was_built_for() -> None:
    user = object()
    world = DemoWorld(user)

    assert world.user is user


def test_a_seeded_object_is_read_back_by_its_key() -> None:
    world = DemoWorld(object()).add_order('PO-4182')

    assert world.order('PO-4182') == 'order:PO-4182'


def test_seeding_returns_the_world_so_calls_chain() -> None:
    world = DemoWorld(object())

    assert world.add_order('PO-1') is world


def test_a_key_seeded_twice_is_refused() -> None:
    world = DemoWorld(object()).add_order('PO-4182')

    with pytest.raises(ValueError, match='order already seeded: PO-4182'):
        world.add_order('PO-4182')


def test_a_key_that_was_never_seeded_names_itself_in_the_failure() -> None:
    world = DemoWorld(object())

    with pytest.raises(KeyError, match='order not seeded: PO-4182'):
        world.order('PO-4182')
