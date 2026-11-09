import { assert } from '../assert.ts';

import type { Point } from '../geometry.ts';


const SELECTOR_CONTROL = 'button, input, select, textarea';


export function isPointHit(element: Element, point: Point): boolean {
    assert(Number.isFinite(point.x), 'a hit test reads a finite point');
    assert(Number.isFinite(point.y), 'a hit test reads a finite point');

    const found = document.elementFromPoint(point.x, point.y);

    if (found === null) {
        return false;
    }

    if (!element.contains(found)) {
        return false;
    }

    const control = found.closest(SELECTOR_CONTROL);

    if (control === null) {
        return true;
    }

    return Reflect.get(control, 'disabled') !== true;
}
