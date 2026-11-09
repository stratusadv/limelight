import { deepEqual, equal, ok } from 'node:assert/strict';
import { test } from 'node:test';

import { boxScrolled, labelPositionOf, spotFrameOf } from './spot.ts';


const VIEWPORT = Object.freeze({ height: 600, width: 800 });


test('spotFrameOf pads a box in the open', () => {
    const frame = spotFrameOf({ height: 20, width: 100, x: 50, y: 60 }, VIEWPORT);

    deepEqual(frame, { height: 36, left: 42, top: 52, width: 116 });
});

test('spotFrameOf keeps the frame inside the viewport margin', () => {
    const frame = spotFrameOf({ height: 5000, width: 5000, x: -100, y: -100 }, VIEWPORT);

    equal(frame.left, 8);
    equal(frame.top, 8);
    equal(frame.left + frame.width, VIEWPORT.width - 8);
    equal(frame.top + frame.height, VIEWPORT.height - 8);
});

test('spotFrameOf collapses a box scrolled out of the viewport', () => {
    const frame = spotFrameOf({ height: 20, width: 100, x: 5000, y: 5000 }, VIEWPORT);

    equal(frame.width, 0);
    equal(frame.height, 0);
});

test('labelPositionOf rises above the frame and stays on screen', () => {
    const frame = { height: 36, left: 42, top: 152, width: 116 };

    deepEqual(labelPositionOf(frame, VIEWPORT), { x: 42, y: 108 });
    deepEqual(labelPositionOf({ ...frame, top: 8 }, VIEWPORT), { x: 42, y: 8 });
    deepEqual(labelPositionOf({ ...frame, left: 790 }, VIEWPORT), { x: 432, y: 108 });

    const narrow = { ...VIEWPORT, width: 100 };

    deepEqual(labelPositionOf({ ...frame, left: 790 }, narrow), { x: 8, y: 108 });
});

test('boxScrolled undoes a scroll and round trips back to the anchor', () => {
    const box = { height: 20, width: 100, x: 50, y: 60 };
    const anchor = { box, label: undefined, scroll: { x: 0, y: 0 } };
    const moved = boxScrolled(anchor, { x: 30, y: 40 });

    deepEqual(moved, { height: 20, width: 100, x: 20, y: 20 });
    deepEqual(boxScrolled(anchor, anchor.scroll), box);

    const reanchored = { box: moved, label: undefined, scroll: { x: 30, y: 40 } };

    deepEqual(boxScrolled(reanchored, anchor.scroll), box);
    ok(moved.width === box.width);
});
