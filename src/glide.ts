import { assert } from './assert.ts';

import type { Point } from './geometry.ts';


export interface GlidePath {
    readonly control: Point;
    readonly overshoot: Point;
    readonly settleStart: number;
    readonly start: Point;
    readonly target: Point;
}

export interface GlideShape {
    readonly bowPx: number;
    readonly durationMs: number;
    readonly overshootPx: number;
}

export interface Move extends Point {
    readonly direct?: boolean;
    readonly ms: number;
}

export interface Route {
    readonly shape: GlideShape;
    readonly start: Point;
    readonly target: Point;
}


const BOW_DISTANCE_FACTOR = 0.12;
const BOW_PX_MAX = 48;
const DISTANCE_FINITE = 'a glide covers a finite distance';
const DISTANCE_PX_MIN = 1;
const DURATION_FINITE = 'a glide lasts a finite time';
const FRACTION_ON_PATH = 'a fraction stays on its path';
const FRAMES_PER_SECOND = 60;
const HALF = 0.5;
const JERK_CUBIC = 10;
const JERK_QUARTIC = 15;
const JERK_QUINTIC = 6;
const OVERSHOOT_DISTANCE_FACTOR = 0.04;
const OVERSHOOT_DISTANCE_PX_MIN = 80;
const OVERSHOOT_PX_MAX = 10;
const PACE_BASE = 0.44;
const PACE_DISTANCE_FACTOR = 0.032;
const PACE_FACTOR_MAX = 2;
const PACE_FACTOR_MIN = 0.5;
const POINT_FINITE = 'a glide stays on finite coordinates';
const SECOND_MS = 1000;
const SETTLE_START = 0.84;
const WEIGHT_CONTROL_FACTOR = 2;
const FRAME_MS = SECOND_MS / FRAMES_PER_SECOND;

const SHAPE_STILL: GlideShape = Object.freeze({
    bowPx: 0,
    durationMs: 0,
    overshootPx: 0,
});


export function frameDeltaOf(deltaMs: number): number {
    assert(Number.isFinite(deltaMs), DURATION_FINITE);

    if (deltaMs <= 0) {
        return FRAME_MS;
    }

    return deltaMs;
}

export function glidePathOf(route: Route): GlidePath {
    const { shape, start, target } = route;
    const xDelta = target.x - start.x;
    const yDelta = target.y - start.y;
    const distance = Math.hypot(xDelta, yDelta);

    assert(distance > 0, 'a glide path covers a distance');
    assert(Number.isFinite(distance), DISTANCE_FINITE);

    const xUnit = xDelta / distance;
    const yUnit = yDelta / distance;
    const xMiddle = start.x + xDelta * HALF;
    const yMiddle = start.y + yDelta * HALF;

    return {
        control: { x: xMiddle - yUnit * shape.bowPx, y: yMiddle + xUnit * shape.bowPx },
        overshoot: {
            x: target.x + xUnit * shape.overshootPx,
            y: target.y + yUnit * shape.overshootPx,
        },
        settleStart: settleStartOf(shape.overshootPx),
        start,
        target,
    };
}

export function glidePointAt(path: GlidePath, fraction: number): Point {
    assert(fraction >= 0, FRACTION_ON_PATH);
    assert(fraction <= 1, FRACTION_ON_PATH);

    if (fraction < path.settleStart) {
        return curvePointAt(path, jerkMinimum(fraction / path.settleStart));
    }

    if (fraction < 1) {
        return settlePointAt(path, (fraction - path.settleStart) / (1 - path.settleStart));
    }

    return path.target;
}

export function glideShapeOf(start: Point, move: Move): GlideShape {
    const delta = { x: move.x - start.x, y: move.y - start.y };
    const distance = Math.hypot(delta.x, delta.y);

    assert(Number.isFinite(distance), DISTANCE_FINITE);
    assert(move.ms >= 0, DURATION_FINITE);

    if (distance < DISTANCE_PX_MIN) {
        return SHAPE_STILL;
    }

    if (move.direct === true) {
        return { ...SHAPE_STILL, durationMs: move.ms };
    }

    return {
        bowPx: bowSignOf(delta) * Math.min(distance * BOW_DISTANCE_FACTOR, BOW_PX_MAX),
        durationMs: durationOf(move, distance),
        overshootPx: overshootOf(distance),
    };
}

export function jerkMinimum(fraction: number): number {
    assert(fraction >= 0, FRACTION_ON_PATH);
    assert(fraction <= 1, FRACTION_ON_PATH);

    const cube = fraction * fraction * fraction;
    const falling = JERK_CUBIC - JERK_QUARTIC * fraction;
    const rising = JERK_QUINTIC * fraction * fraction;
    const progress = cube * (falling + rising);

    assert(Number.isFinite(progress), FRACTION_ON_PATH);

    return progress;
}


function bowSignOf(delta: Point): number {
    assert(Number.isFinite(delta.x), POINT_FINITE);
    assert(Number.isFinite(delta.y), POINT_FINITE);

    if (delta.x * delta.y >= 0) {
        return -1;
    }

    return 1;
}

function curvePointAt(path: GlidePath, progress: number): Point {
    assert(Number.isFinite(progress), FRACTION_ON_PATH);
    assert(Number.isFinite(path.control.x), POINT_FINITE);
    assert(Number.isFinite(path.control.y), POINT_FINITE);

    const inverse = 1 - progress;
    const weightStart = inverse * inverse;
    const weightControl = WEIGHT_CONTROL_FACTOR * inverse * progress;
    const weightEnd = progress * progress;

    return {
        x: weightStart * path.start.x
            + weightControl * path.control.x
            + weightEnd * path.overshoot.x,
        y: weightStart * path.start.y
            + weightControl * path.control.y
            + weightEnd * path.overshoot.y,
    };
}

function durationOf(move: Move, distance: number): number {
    assert(move.ms >= 0, DURATION_FINITE);
    assert(distance >= DISTANCE_PX_MIN, DISTANCE_FINITE);

    const paced = move.ms * (PACE_BASE + PACE_DISTANCE_FACTOR * Math.sqrt(distance));
    const pacedMin = Math.max(move.ms * PACE_FACTOR_MIN, paced);
    const durationMs = Math.round(Math.min(move.ms * PACE_FACTOR_MAX, pacedMin));

    assert(Number.isFinite(durationMs), DURATION_FINITE);

    return durationMs;
}

function overshootOf(distance: number): number {
    assert(distance >= DISTANCE_PX_MIN, DISTANCE_FINITE);
    assert(Number.isFinite(distance), DISTANCE_FINITE);

    if (distance < OVERSHOOT_DISTANCE_PX_MIN) {
        return 0;
    }

    const overshootPx = Math.min(distance * OVERSHOOT_DISTANCE_FACTOR, OVERSHOOT_PX_MAX);

    assert(overshootPx <= OVERSHOOT_PX_MAX, DISTANCE_FINITE);

    return overshootPx;
}

function settlePointAt(path: GlidePath, settle: number): Point {
    assert(settle >= 0, FRACTION_ON_PATH);
    assert(settle < 1, FRACTION_ON_PATH);

    const inverse = 1 - settle;
    const eased = 1 - inverse * inverse;

    return {
        x: path.overshoot.x + (path.target.x - path.overshoot.x) * eased,
        y: path.overshoot.y + (path.target.y - path.overshoot.y) * eased,
    };
}

function settleStartOf(overshootPx: number): number {
    assert(overshootPx >= 0, DISTANCE_FINITE);
    assert(overshootPx <= OVERSHOOT_PX_MAX, DISTANCE_FINITE);

    if (overshootPx > 0) {
        return SETTLE_START;
    }

    return 1;
}
