import { equal } from 'node:assert/strict';
import { test } from 'node:test';

import { isPointInside } from './geometry.ts';


const EDGES = Object.freeze({
    bottom: 40,
    left: 10,
    right: 30,
    top: 20,
});


test('isPointInside counts every edge as inside', () => {
    equal(isPointInside(EDGES, { x: 20, y: 30 }), true);
    equal(isPointInside(EDGES, { x: 10, y: 20 }), true);
    equal(isPointInside(EDGES, { x: 30, y: 40 }), true);
});

test('isPointInside rejects a point past each edge', () => {
    equal(isPointInside(EDGES, { x: 9.999, y: 30 }), false);
    equal(isPointInside(EDGES, { x: 30.001, y: 30 }), false);
    equal(isPointInside(EDGES, { x: 20, y: 19.999 }), false);
    equal(isPointInside(EDGES, { x: 20, y: 40.001 }), false);
});
