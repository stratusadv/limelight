import { elementBuild, elementFind, elementRemove, pixels } from './dom.ts';
import { assert } from './assert.ts';

import type { Box, Point } from './geometry.ts';


export interface SpotAnchor {
    readonly box: Box;
    readonly label: string | undefined;
    readonly scroll: Point;
}

export interface SpotFrame {
    readonly height: number;
    readonly left: number;
    readonly top: number;
    readonly width: number;
}

export interface SpotSurface {
    readonly spot: (target: SpotTarget) => void;
    readonly spotClear: () => void;
}

export interface SpotTarget {
    readonly box: Box;
    readonly dim?: boolean;
    readonly label?: string;
}

export interface Viewport {
    readonly height: number;
    readonly width: number;
}


const BOX_SIZED = 'a spotlit box has a size';
const CLASS_UNDIMMED = 'nodim';
const FRAME_INSIDE = 'a spot frame stays on screen';
const LABEL_EDGE_PX = 8;
const LABEL_ID = 'limelight-spot-label';
const LABEL_RISE_PX = 44;
const LABEL_WIDTH_PX = 368;
const LIVE = 'a spot lights a live page';
const SCROLL_FINITE = 'a scroll offset is a finite number';
const SPOT_ID = 'limelight-spot';
const SPOT_LISTENER_KEY = '__limelightSpotReposition';
const SPOT_PAD_PX = 8;
const VIEWPORT_SIZED = 'a viewport has a size';


export class Spot {
    #anchor: SpotAnchor | undefined = undefined;
    readonly #onScroll = this.#scrolled.bind(this);

    public constructor() {
        assert(document.defaultView !== null, LIVE);
        assert(this.#anchor === undefined, 'a new spot lights nothing');

        const listener: unknown = Reflect.get(globalThis, SPOT_LISTENER_KEY);

        if (isScrollListener(listener)) {
            window.removeEventListener('scroll', listener);
        }

        Reflect.set(globalThis, SPOT_LISTENER_KEY, this.#onScroll);
        window.addEventListener('scroll', this.#onScroll, { passive: true });
    }

    #scrolled(): void {
        assert(document.defaultView !== null, LIVE);
        assert(Number.isFinite(window.scrollY), SCROLL_FINITE);

        if (this.#anchor === undefined) {
            return;
        }

        spotPlace(boxScrolled(this.#anchor, scrollOf()), this.#anchor.label);
    }

    #show(target: SpotTarget): void {
        assert(target.box.width >= 0, BOX_SIZED);
        assert(target.box.height >= 0, BOX_SIZED);

        const spot = elementBuild(SPOT_ID);

        spot.classList.toggle(CLASS_UNDIMMED, target.dim === false);

        if (isLabelled(target.label)) {
            elementBuild(LABEL_ID);
        } else {
            elementRemove(LABEL_ID);
        }

        this.#anchor = { box: target.box, label: target.label, scroll: scrollOf() };

        spotPlace(target.box, target.label);
    }

    public surface(): SpotSurface {
        assert(document.defaultView !== null, LIVE);
        assert(this.#anchor === undefined, 'a surface is taken before the first spot');

        return {
            spot: (target): void => {
                this.#show(target);
            },
            spotClear: (): void => {
                this.#anchor = undefined;

                elementRemove(SPOT_ID);
                elementRemove(LABEL_ID);
            },
        };
    }
}


export function boxScrolled(anchor: SpotAnchor, scroll: Point): Box {
    assert(Number.isFinite(scroll.x), SCROLL_FINITE);
    assert(Number.isFinite(scroll.y), SCROLL_FINITE);

    return {
        height: anchor.box.height,
        width: anchor.box.width,
        x: anchor.box.x + (anchor.scroll.x - scroll.x),
        y: anchor.box.y + (anchor.scroll.y - scroll.y),
    };
}

export function labelPositionOf(frame: SpotFrame, viewport: Viewport): Point {
    assert(viewport.width >= 0, VIEWPORT_SIZED);
    assert(frame.top >= SPOT_PAD_PX, FRAME_INSIDE);

    const leftMax = viewport.width - LABEL_WIDTH_PX;

    return {
        x: Math.max(LABEL_EDGE_PX, Math.min(frame.left, leftMax)),
        y: Math.max(LABEL_EDGE_PX, frame.top - LABEL_RISE_PX),
    };
}

export function spotFrameOf(box: Box, viewport: Viewport): SpotFrame {
    assert(box.width >= 0, BOX_SIZED);
    assert(box.height >= 0, BOX_SIZED);
    assert(viewport.width >= 0, VIEWPORT_SIZED);
    assert(viewport.height >= 0, VIEWPORT_SIZED);

    const left = Math.max(SPOT_PAD_PX, box.x - SPOT_PAD_PX);
    const top = Math.max(SPOT_PAD_PX, box.y - SPOT_PAD_PX);
    const right = Math.min(viewport.width - SPOT_PAD_PX, box.x + box.width + SPOT_PAD_PX);
    const bottom = Math.min(viewport.height - SPOT_PAD_PX, box.y + box.height + SPOT_PAD_PX);
    const height = Math.max(0, bottom - top);
    const width = Math.max(0, right - left);

    assert(height >= 0, FRAME_INSIDE);
    assert(width >= 0, FRAME_INSIDE);

    return { height, left, top, width };
}


function isLabelled(label: string | undefined): label is string {
    return (label ?? '').length > 0;
}

function isScrollListener(value: unknown): value is EventListener {
    return typeof value === 'function';
}

function labelPlace(label: string, frame: SpotFrame, viewport: Viewport): void {
    assert(label.length > 0, 'a placed label has text');
    assert(frame.width >= 0, FRAME_INSIDE);

    const node = elementFind(LABEL_ID);

    if (node === undefined) {
        return;
    }

    const position = labelPositionOf(frame, viewport);

    node.textContent = label;
    node.style.top = pixels(position.y);
    node.style.left = pixels(position.x);
}

function scrollOf(): Point {
    assert(Number.isFinite(window.scrollX), SCROLL_FINITE);
    assert(Number.isFinite(window.scrollY), SCROLL_FINITE);

    return { x: window.scrollX, y: window.scrollY };
}

function spotPlace(box: Box, label: string | undefined): void {
    assert(box.width >= 0, BOX_SIZED);
    assert(box.height >= 0, BOX_SIZED);

    const spot = elementFind(SPOT_ID);

    if (spot === undefined) {
        return;
    }

    const viewport = { height: window.innerHeight, width: window.innerWidth };
    const frame = spotFrameOf(box, viewport);

    spot.style.top = pixels(frame.top);
    spot.style.left = pixels(frame.left);
    spot.style.width = pixels(frame.width);
    spot.style.height = pixels(frame.height);

    if (isLabelled(label)) {
        labelPlace(label, frame, viewport);
    }
}
