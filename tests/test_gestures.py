from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING

from limelight.gestures import slide_geometry, slide_to_end

from fakes import FakeLocator, FakePage

if TYPE_CHECKING:
    from collections.abc import Mapping


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(to_be_visible=lambda: None)


def locator_build(box: Mapping[str, float]) -> FakeLocator:
    boxes = [box]

    return FakeLocator(boxes=boxes)


def test_slide_drags_thumb_to_track_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.gestures.expect', expect_stub)

    page = FakePage()
    track_box = {'x': 0, 'y': 10, 'width': 200, 'height': 20}
    thumb_box = {'x': 0, 'y': 10, 'width': 20, 'height': 20}

    track = locator_build(track_box)
    thumb = locator_build(thumb_box)

    slide_to_end(page.as_page(), track=track.as_locator(), thumb=thumb.as_locator())

    assert page.mouse.actions == [
        ('move', 10.0, 20.0, 1),
        ('down',),
        ('move', 200.0, 20.0, 25),
        ('up',),
    ]


def test_slide_rejects_missing_track_box(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.gestures.expect', expect_stub)

    page = FakePage()
    thumb_box = {'x': 0, 'y': 10, 'width': 20, 'height': 20}

    thumb = locator_build(thumb_box)

    with pytest.raises(ValueError, match='track'):
        slide_to_end(page.as_page(), track=FakeLocator().as_locator(), thumb=thumb.as_locator())


def test_slide_rejects_non_positive_step_count() -> None:
    page = FakePage()

    with pytest.raises(ValueError, match='step_count'):
        slide_to_end(
            page.as_page(),
            track=FakeLocator().as_locator(),
            thumb=FakeLocator().as_locator(),
            step_count=0,
        )


def test_a_thumb_without_a_box_is_refused() -> None:
    track = FakeLocator([{'x': 0, 'y': 0, 'width': 200, 'height': 20}])
    thumb = FakeLocator()

    with pytest.raises(ValueError, match='thumb has no bounding box'):
        slide_geometry(track=track.as_locator(), thumb=thumb.as_locator())
