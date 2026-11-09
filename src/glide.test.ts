import { deepEqual, equal, ok, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { frameDeltaOf, glidePathOf, glidePointAt, glideShapeOf, jerkMinimum } from './glide.ts';
import { AssertionError } from './assert.ts';

import type { GlideShape, Move } from './glide.ts';
import type { Point } from './geometry.ts';


const CLOSE = 1e-9;
const ORIGIN: Point = Object.freeze({ x: 0, y: 0 });
const SAMPLE_COUNT = 1000;
const SHAPE_STRAIGHT: GlideShape = Object.freeze({ bowPx: 0, durationMs: 500, overshootPx: 0 });

const TARGET: Move = Object.freeze({ ms: 500, x: 300, y: 400 });


test('frameDeltaOf keeps a forward step and stands in for a stalled clock', () => {
    equal(frameDeltaOf(25), 25);
    equal(frameDeltaOf(0), 1000 / 60);
    equal(frameDeltaOf(-5), 1000 / 60);
});

test('jerkMinimum rises from rest to rest', () => {
    equal(jerkMinimum(0), 0);
    equal(jerkMinimum(1), 1);

    for (let index = 0; index < SAMPLE_COUNT; index += 1) {
        const earlier = jerkMinimum(index / SAMPLE_COUNT);
        const later = jerkMinimum((index + 1) / SAMPLE_COUNT);

        ok(later >= earlier);
    }
});

test('jerkMinimum mirrors around its midpoint', () => {
    for (let index = 0; index <= SAMPLE_COUNT; index += 1) {
        const fraction = index / SAMPLE_COUNT;

        ok(Math.abs(jerkMinimum(fraction) + jerkMinimum(1 - fraction) - 1) < CLOSE);
    }
});

test('jerkMinimum matches the published polynomial', () => {
    for (let index = 0; index <= SAMPLE_COUNT; index += 1) {
        const fraction = index / SAMPLE_COUNT;
        const expected = 10 * fraction ** 3 - 15 * fraction ** 4 + 6 * fraction ** 5;

        ok(Math.abs(jerkMinimum(fraction) - expected) < CLOSE);
    }
});

test('glideShapeOf holds still under one pixel', () => {
    const shape = glideShapeOf(ORIGIN, { ms: 500, x: 0.5, y: 0.5 });

    deepEqual(shape, { bowPx: 0, durationMs: 0, overshootPx: 0 });
});

test('glideShapeOf takes a direct move as asked', () => {
    const shape = glideShapeOf(ORIGIN, { direct: true, ms: 120, x: 300, y: 400 });

    deepEqual(shape, { bowPx: 0, durationMs: 120, overshootPx: 0 });
});

test('glideShapeOf paces a move between half and double the reference', () => {
    for (let distance = 1; distance < 5000; distance += 7) {
        const { durationMs } = glideShapeOf(ORIGIN, { ms: 500, x: distance, y: 0 });

        ok(durationMs >= 250);
        ok(durationMs <= 1000);
    }
});

test('glideShapeOf lengthens with distance', () => {
    const near = glideShapeOf(ORIGIN, { ms: 500, x: 40, y: 0 });
    const far = glideShapeOf(ORIGIN, { ms: 500, x: 800, y: 0 });

    ok(far.durationMs > near.durationMs);
});

test('glideShapeOf bows away from the diagonal it travels', () => {
    const falling = glideShapeOf(ORIGIN, { ms: 500, x: 300, y: 400 });
    const rising = glideShapeOf(ORIGIN, { ms: 500, x: 300, y: -400 });

    ok(falling.bowPx < 0);
    ok(rising.bowPx > 0);
    ok(Math.abs(falling.bowPx) <= 48);
});

test('glideShapeOf overshoots only a long move', () => {
    equal(glideShapeOf(ORIGIN, { ms: 500, x: 79, y: 0 }).overshootPx, 0);
    ok(glideShapeOf(ORIGIN, { ms: 500, x: 80, y: 0 }).overshootPx > 0);
    ok(glideShapeOf(ORIGIN, { ms: 500, x: 5000, y: 0 }).overshootPx <= 10);
});

test('glidePathOf refuses a path of no length', () => {
    throws(
        () => {
            glidePathOf({ shape: SHAPE_STRAIGHT, start: ORIGIN, target: ORIGIN });
        },
        AssertionError,
    );
});

test('glidePointAt starts at the start and ends at the target', () => {
    const shape = glideShapeOf(ORIGIN, TARGET);
    const path = glidePathOf({ shape, start: ORIGIN, target: TARGET });
    const first = glidePointAt(path, 0);

    ok(Math.abs(first.x) < CLOSE);
    ok(Math.abs(first.y) < CLOSE);
    deepEqual(glidePointAt(path, 1), TARGET);
});

test('glidePointAt reaches the overshoot then eases back without a jump', () => {
    const shape = glideShapeOf(ORIGIN, TARGET);
    const path = glidePathOf({ shape, start: ORIGIN, target: TARGET });
    const before = glidePointAt(path, path.settleStart - CLOSE);
    const after = glidePointAt(path, path.settleStart);

    ok(Math.hypot(before.x - path.overshoot.x, before.y - path.overshoot.y) < 1e-3);
    ok(Math.hypot(after.x - path.overshoot.x, after.y - path.overshoot.y) < CLOSE);
});

test('glidePointAt never steps further than the path allows between frames', () => {
    const shape = glideShapeOf(ORIGIN, TARGET);
    const path = glidePathOf({ shape, start: ORIGIN, target: TARGET });
    let previous = glidePointAt(path, 0);

    for (let index = 1; index <= SAMPLE_COUNT; index += 1) {
        const point = glidePointAt(path, index / SAMPLE_COUNT);

        ok(Math.hypot(point.x - previous.x, point.y - previous.y) < 10);

        previous = point;
    }
});

test('glidePointAt runs straight when the shape has no bow or overshoot', () => {
    const path = glidePathOf({ shape: SHAPE_STRAIGHT, start: ORIGIN, target: TARGET });

    equal(path.settleStart, 1);

    for (let index = 0; index < SAMPLE_COUNT; index += 1) {
        const point = glidePointAt(path, index / SAMPLE_COUNT);

        ok(Math.abs(point.x * TARGET.y - point.y * TARGET.x) < 1e-6);
    }
});

test('glidePointAt refuses a time before the start', () => {
    const path = glidePathOf({ shape: SHAPE_STRAIGHT, start: ORIGIN, target: TARGET });

    throws(
        () => {
            glidePointAt(path, -0.1);
        },
        AssertionError,
    );
});
