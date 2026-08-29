from __future__ import annotations

from limelight.export.chapters import chapters_render

from events import events_sample


def test_chapters_lists_title_events() -> None:
    assert chapters_render(events_sample()) == '00:00 Order Approval\n'


def test_chapters_empty_without_title_events() -> None:
    assert chapters_render([]) == ''
