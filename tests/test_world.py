from __future__ import annotations

import pytest

from limelight.world import WorldBase


def test_claim_rejects_duplicates() -> None:
    world = WorldBase()
    registry = {'truck': object()}

    with pytest.raises(ValueError, match='already seeded'):
        world._claim(registry, 'truck', 'shipment')


def test_claim_allows_new_names() -> None:
    world = WorldBase()
    registry: dict[str, object] = {}

    world._claim(registry, 'truck', 'shipment')


def test_require_returns_seeded_value() -> None:
    world = WorldBase()
    shipment = object()
    registry = {'truck': shipment}

    assert world._require(registry, 'truck', 'shipment') is shipment


def test_require_rejects_missing_names() -> None:
    world = WorldBase()
    registry: dict[str, object] = {}

    with pytest.raises(KeyError, match='not seeded'):
        world._require(registry, 'truck', 'shipment')
