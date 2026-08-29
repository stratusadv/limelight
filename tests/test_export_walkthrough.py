from __future__ import annotations

from typing import TYPE_CHECKING

from limelight.export.walkthrough import markdown_render, walkthrough_export

from events import events_sample

if TYPE_CHECKING:
    from pathlib import Path


def test_markdown_renders_walkthrough() -> None:
    content = markdown_render(events_sample(), title='Demo')

    assert '# Demo' in content
    assert '# Order Approval' in content
    assert '*Chapter One*' in content
    assert '## Open the order' in content
    assert 'Navigate to it.' in content
    assert '- Click "Orders"' in content
    assert '![orders](01-orders.png)' in content
    assert '| Orders | 3 | 5 | +2 |' in content


def test_markdown_renders_action_bullets() -> None:
    events: list[dict[str, object]] = [
        {'event': 'click', 'offset_ms': 0, 'target': 'Approve'},
        {'event': 'fill', 'offset_ms': 1, 'target': 'Order number', 'value': 'SO-100'},
        {'event': 'fill', 'offset_ms': 2, 'target': '', 'value': 'note'},
        {'event': 'select', 'offset_ms': 3, 'target': '', 'option': 'Approved'},
        {'event': 'press', 'offset_ms': 4, 'target': '', 'key': 'Enter'},
        {'event': 'check', 'offset_ms': 5, 'target': 'Urgent'},
        {'event': 'hover', 'offset_ms': 6, 'target': 'Totals'},
        {'event': 'slide', 'offset_ms': 7, 'target': ''},
        {'event': 'uncheck', 'offset_ms': 8, 'target': 'Urgent'},
    ]

    content = markdown_render(events)

    assert '- Click "Approve"' in content
    assert '- Fill "Order number" with "SO-100"' in content
    assert '- Type "note"' in content
    assert '- Select "Approved"' in content
    assert '- Press Enter' in content
    assert '- Check "Urgent"' in content
    assert '- Hover over "Totals"' in content
    assert '- Slide to confirm' in content
    assert '- Uncheck "Urgent"' in content


def test_markdown_skips_actions_without_targets() -> None:
    events: list[dict[str, object]] = [
        {'event': 'click', 'offset_ms': 0, 'target': ''},
    ]

    assert markdown_render(events) == '\n'


def test_markdown_skips_unknown_events() -> None:
    events: list[dict[str, object]] = [
        {'event': 'mystery', 'offset_ms': 0},
    ]

    assert markdown_render(events) == '\n'


def test_walkthrough_export_carries_the_title(tmp_path: Path) -> None:
    path = walkthrough_export('Order Approval').export(events_sample(), tmp_path)

    assert path.read_text(encoding='utf-8').startswith('# Order Approval\n')


def test_events_missing_their_detail_render_no_bullet() -> None:
    events: list[dict[str, object]] = [
        {'event': 'press', 'offset_ms': 0, 'target': 'Search', 'key': ''},
        {'event': 'screenshot', 'offset_ms': 1, 'name': 'shot', 'file': ''},
        {'event': 'select', 'offset_ms': 2, 'target': 'Status', 'option': ''},
        {'event': 'spotlight', 'offset_ms': 3, 'label': ''},
        {'event': 'click', 'offset_ms': 4, 'target': ''},
        {'event': '', 'offset_ms': 5, 'target': 'Orders'},
    ]

    content = markdown_render(events, title='Demo')

    assert content.strip() == '# Demo'


def test_a_card_without_a_subtitle_or_rows_renders_plainly() -> None:
    events: list[dict[str, object]] = [
        {'event': 'title', 'offset_ms': 0, 'title': 'Chapter', 'kicker': '', 'subtitle': ''},
        {'event': 'metrics', 'offset_ms': 1, 'title': 'Totals', 'rows': 'not-a-list'},
    ]

    content = markdown_render(events, title='Demo')

    assert '# Chapter' in content
    assert 'Totals' in content
    assert '|' not in content


def test_a_metrics_card_carries_its_subtitle() -> None:
    events: list[dict[str, object]] = [{
        'event': 'metrics',
        'offset_ms': 0,
        'title': 'Totals',
        'subtitle': 'Before and after',
        'rows': [],
    }]

    content = markdown_render(events, title='Demo')

    assert 'Before and after' in content


def test_an_action_without_a_target_renders_no_bullet() -> None:
    events: list[dict[str, object]] = [{'event': 'hover', 'offset_ms': 0, 'target': ''}]

    assert markdown_render(events, title='Demo').strip() == '# Demo'
