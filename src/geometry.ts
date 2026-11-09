import { assert } from './assert.ts';


export interface Edges {
    readonly bottom: number;
    readonly left: number;
    readonly right: number;
    readonly top: number;
}

export interface Point {
    readonly x: number;
    readonly y: number;
}

export interface Box extends Point {
    readonly height: number;
    readonly width: number;
}


export function isPointInside(edges: Edges, point: Point): boolean {
    assert(edges.left <= edges.right, 'a rectangle runs left to right');
    assert(edges.top <= edges.bottom, 'a rectangle runs top to bottom');

    if (point.x < edges.left) {
        return false;
    }

    if (point.x > edges.right) {
        return false;
    }

    if (point.y < edges.top) {
        return false;
    }

    return point.y <= edges.bottom;
}
