from __future__ import annotations


def events_sample() -> list[dict[str, object]]:
    metrics_rows = [
        {
            'label': 'Orders',
            'before': '3',
            'after': '5',
            'delta': '+2',
            'direction': 'up',
            'sentiment': 'good',
        },
    ]

    return [
        {
            'event': 'title',
            'offset_ms': 0,
            'title': 'Order Approval',
            'kicker': 'Chapter One',
            'subtitle': 'Draft to approved.',
        },
        {
            'event': 'narrate',
            'offset_ms': 2000,
            'title': 'Open the order',
            'body': 'Navigate to it.',
            'step': 'Navigate',
        },
        {
            'event': 'spotlight',
            'offset_ms': 4000,
            'label': 'Click "Orders"',
        },
        {
            'event': 'screenshot',
            'offset_ms': 5000,
            'name': 'orders',
            'file': '01-orders.png',
        },
        {
            'event': 'metrics',
            'offset_ms': 6000,
            'title': 'Totals',
            'kicker': '',
            'subtitle': '',
            'rows': metrics_rows,
        },
    ]
