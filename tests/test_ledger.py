from __future__ import annotations

import pytest

from limelight.ledger import Ledger


def test_snapshot_reads_probes() -> None:
    ledger = Ledger().track('Orders', lambda: 3, unit='orders')

    assert ledger.snapshot() == {'Orders': 3.0}


def test_rows_compute_deltas_and_directions() -> None:
    values = {'Orders': 3.0, 'Weight': 100.0, 'Drafts': 5.0}

    ledger = (
        Ledger()
        .track('Orders', lambda: values['Orders'], unit='orders')
        .track('Weight', lambda: values['Weight'], unit='lb')
        .track('Drafts', lambda: values['Drafts'])
    )

    before = ledger.snapshot()

    values['Orders'] = 5.0
    values['Weight'] = 40.0

    rows = ledger.rows(before)

    assert rows[0] == {
        'label': 'Orders',
        'before': '3 orders',
        'after': '5 orders',
        'delta': '+2 orders',
        'direction': 'up',
        'sentiment': 'good',
    }
    assert rows[1]['delta'] == '-60 lb'
    assert rows[1]['direction'] == 'down'
    assert rows[1]['sentiment'] == 'bad'
    assert rows[2]['delta'] == '0'
    assert rows[2]['direction'] == 'flat'
    assert rows[2]['sentiment'] == 'flat'


def test_rows_format_fractions_with_two_decimals() -> None:
    ledger = Ledger().track('Yield', lambda: 1234.5, unit='kg')

    before = {'Yield': 0.0}

    rows = ledger.rows(before)

    assert rows[0]['after'] == '1,234.50 kg'


def test_improves_down_flips_sentiment() -> None:
    values = {'Errors': 5.0}
    ledger = Ledger().track('Errors', lambda: values['Errors'], improves='down', unit='errors')

    before = ledger.snapshot()

    values['Errors'] = 2.0

    rows = ledger.rows(before)

    assert rows[0]['direction'] == 'down'
    assert rows[0]['sentiment'] == 'good'


def test_improves_invalid_rejected() -> None:
    with pytest.raises(ValueError, match='improves'):
        Ledger().track('Errors', lambda: 0.0, improves='sideways')


def test_rows_reject_values_missing_a_tracked_metric() -> None:
    ledger = Ledger().track('Yield', lambda: 1.0, unit='kg').track('Waste', lambda: 2.0, unit='kg')

    before = {'Yield': 0.0}

    with pytest.raises(KeyError, match='Waste'):
        ledger.rows(before)
