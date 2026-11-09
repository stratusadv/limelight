import { equal, ok } from 'node:assert/strict';
import { test } from 'node:test';

import { panelTopOf } from './select.ts';


const BOX = Object.freeze({ height: 30, width: 200, x: 40, y: 100 });


test('panelTopOf opens below when the panel fits', () => {
    equal(panelTopOf(BOX, { panel: 120, viewport: 600 }), 134);
});

test('panelTopOf fits exactly against the bottom margin', () => {
    equal(panelTopOf(BOX, { panel: 458, viewport: 600 }), 134);
    equal(panelTopOf(BOX, { panel: 459, viewport: 600 }), 8);
});

test('panelTopOf opens above when below would overflow', () => {
    const box = { ...BOX, y: 500 };
    const top = panelTopOf(box, { panel: 120, viewport: 600 });

    equal(top, 376);
    ok(top + 120 <= box.y);
});

test('panelTopOf never leaves the top margin', () => {
    equal(panelTopOf({ ...BOX, y: 20 }, { panel: 590, viewport: 600 }), 8);
});
