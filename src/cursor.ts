import {
    elementBuild,
    elementFind,
    elementHide,
    elementRemove,
    elementShow,
    pixels,
} from './dom.ts';
import { frameDeltaOf, glidePathOf, glidePointAt, glideShapeOf } from './glide.ts';
import { sessionRead, sessionWrite } from './session.ts';
import { assert } from './assert.ts';

import type { GlidePath, Move } from './glide.ts';
import type { Point } from './geometry.ts';


export interface CursorSurface {
    readonly cursorHide: () => void;
    readonly cursorMove: (move: Move) => number;
    readonly cursorPulse: () => void;
    readonly cursorRemove: () => void;
    readonly cursorShow: () => void;
}

interface Glide {
    readonly cursor: HTMLElement;
    readonly durationMs: number;
    readonly path: GlidePath;
}


const ATTACHED = 'the drawn cursor sits in the page';
const CLASS_PULSE = 'pulse';
const CURSOR_ID = 'limelight-cursor';
const CURSOR_POSITION_KEY = 'limelight-cursor-position';
const CURSOR_PULSE_MS = 450;
const ELAPSED_FORWARD = 'a glide only moves forward in time';
const GLIDE_STARTED = 'a frame belongs to a started glide';
const HALF = 0.5;
const LIVE = 'the cursor is drawn on a live page';
const PIXELS_UNIT = 'px';
const POINT_FINITE = 'the cursor stays on finite coordinates';
const POSITION_PART_COUNT = 2;


export class Cursor {
    #elapsedMs = 0;
    #frame: number | undefined = undefined;
    #glide: Glide | undefined = undefined;
    readonly #onFrame = this.#frameStep.bind(this);
    #stampPrevious: number | undefined = undefined;

    #frameStep(stamp: number): void {
        const glide = this.#glide;

        assert(glide !== undefined, GLIDE_STARTED);
        assert(glide.durationMs > 0, GLIDE_STARTED);
        assert(this.#elapsedMs >= 0, ELAPSED_FORWARD);

        if (this.#stampPrevious !== undefined) {
            this.#elapsedMs += frameDeltaOf(stamp - this.#stampPrevious);
        }

        this.#stampPrevious = stamp;

        const fraction = Math.min(1, this.#elapsedMs / glide.durationMs);

        cursorPlace(glide.cursor, glidePointAt(glide.path, fraction));

        this.#frame = undefined;

        if (fraction < 1) {
            this.#frame = requestAnimationFrame(this.#onFrame);
        }
    }

    #glideCancel(): void {
        assert(this.#elapsedMs >= 0, ELAPSED_FORWARD);
        assert(document.defaultView !== null, LIVE);

        if (this.#frame !== undefined) {
            cancelAnimationFrame(this.#frame);
        }

        this.#frame = undefined;
    }

    #glideStart(glide: Glide): void {
        assert(glide.durationMs > 0, GLIDE_STARTED);
        assert(this.#frame === undefined, 'one glide runs at a time');

        this.#elapsedMs = 0;
        this.#glide = glide;
        this.#stampPrevious = undefined;
        this.#frame = requestAnimationFrame(this.#onFrame);
    }

    #move(move: Move): number {
        assert(Number.isFinite(move.x), POINT_FINITE);
        assert(Number.isFinite(move.y), POINT_FINITE);

        const cursor = cursorArrived();

        elementShow(cursor);
        sessionWrite({ key: CURSOR_POSITION_KEY, value: `${String(move.x)},${String(move.y)}` });

        const start = cursorPositionOf(cursor);
        const target = { x: move.x, y: move.y };
        const shape = glideShapeOf(start, move);
        const { durationMs } = shape;

        assert(durationMs >= 0, ELAPSED_FORWARD);

        this.#glideCancel();

        if (durationMs <= 0) {
            cursorPlace(cursor, target);

            return durationMs;
        }

        const path = glidePathOf({ shape, start, target });

        this.#glideStart({ cursor, durationMs, path });

        return durationMs;
    }

    public surface(): CursorSurface {
        assert(this.#elapsedMs === 0, ELAPSED_FORWARD);
        assert(this.#frame === undefined, 'a surface is taken before the first glide');

        return {
            cursorHide: (): void => {
                elementHide(CURSOR_ID);
            },
            cursorMove: (move): number => this.#move(move),
            cursorPulse: (): void => {
                cursorPulse();
            },
            cursorRemove: (): void => {
                elementRemove(CURSOR_ID);
            },
            cursorShow: (): void => {
                cursorShow();
            },
        };
    }
}


function cursorArrived(): HTMLElement {
    assert(document.defaultView !== null, LIVE);

    const found = elementFind(CURSOR_ID);

    if (found !== undefined) {
        return found;
    }

    const cursor = elementBuild(CURSOR_ID);

    cursorPlace(cursor, cursorOrigin());
    cursor.getBoundingClientRect();

    assert(cursor.isConnected, ATTACHED);

    return cursor;
}

function cursorOrigin(): Point {
    assert(Number.isFinite(window.innerWidth), POINT_FINITE);
    assert(Number.isFinite(window.innerHeight), POINT_FINITE);

    return cursorPositionStored() ?? {
        x: window.innerWidth * HALF,
        y: window.innerHeight * HALF,
    };
}

function cursorPlace(cursor: HTMLElement, point: Point): void {
    assert(Number.isFinite(point.x), POINT_FINITE);
    assert(Number.isFinite(point.y), POINT_FINITE);

    cursor.style.left = pixels(point.x);
    cursor.style.top = pixels(point.y);
}

function cursorPositionOf(cursor: HTMLElement): Point {
    const x = pixelsParsed(cursor.style.left);
    const y = pixelsParsed(cursor.style.top);

    assert(Number.isFinite(x), POINT_FINITE);
    assert(Number.isFinite(y), POINT_FINITE);

    return { x, y };
}

function cursorPositionStored(): Point | undefined {
    assert(document.defaultView !== null, LIVE);

    const raw = sessionRead(CURSOR_POSITION_KEY);

    if (raw === undefined) {
        return undefined;
    }

    const [xText, yText] = raw.split(',', POSITION_PART_COUNT);
    const x = Number(xText);
    const y = Number(yText);

    if (!Number.isFinite(x)) {
        return undefined;
    }

    if (!Number.isFinite(y)) {
        return undefined;
    }

    return { x, y };
}

function cursorPulse(): void {
    const cursor = elementFind(CURSOR_ID);

    if (cursor === undefined) {
        return;
    }

    assert(cursor.isConnected, ATTACHED);

    cursor.classList.remove(CLASS_PULSE);
    cursor.getBoundingClientRect();
    cursor.classList.add(CLASS_PULSE);

    assert(cursor.classList.contains(CLASS_PULSE), 'a pulse plays on the drawn cursor');

    setTimeout(
        () => {
            cursor.classList.remove(CLASS_PULSE);
        },
        CURSOR_PULSE_MS,
    );
}

function cursorShow(): void {
    const cursor = elementFind(CURSOR_ID);

    assert(document.defaultView !== null, LIVE);

    if (cursor === undefined) {
        return;
    }

    assert(cursor.isConnected, ATTACHED);

    elementShow(cursor);
}

function pixelsParsed(text: string): number {
    assert(!text.includes(' '), 'a CSS length is one token');

    const value = Number(text.replace(PIXELS_UNIT, ''));

    if (Number.isNaN(value)) {
        return 0;
    }

    return value;
}
