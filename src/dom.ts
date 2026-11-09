import { assert } from './assert.ts';


export type Printable = number | string | null | undefined;

export interface NodeShape {
    readonly children?: readonly Node[];
    readonly classes?: string;
    readonly id?: string;
    readonly text?: Printable;
}


const ATTACHED = 'an overlay element sits in the page';
const CLASS_SHOWN = 'show';
const FRAME_SHOW_KEY = 'showFrame';
const ID_NAMED = 'an overlay element carries a limelight id';
const ID_PREFIX = 'limelight-';
const PIXELS_FINITE = 'a CSS length is a finite number';
const PIXELS_MAX = 1_000_000_000;
const PIXELS_SANE = 'a CSS length stays within the page';
const SHAPE_ONE = 'a node carries text or children, never both';
const TAG_NAMED = 'a node names its tag';


export function elementBuild(id: string): HTMLElement {
    const found = elementFind(id);

    if (found !== undefined) {
        return found;
    }

    const node = nodeOf('div', { id });

    document.body.append(node);

    assert(node.isConnected, ATTACHED);
    assert(node.id === id, ID_NAMED);

    return node;
}

export function elementFind(id: string): HTMLElement | undefined {
    assert(id.startsWith(ID_PREFIX), ID_NAMED);
    assert(id.length > ID_PREFIX.length, ID_NAMED);

    const node = document.querySelector(`#${id}`);

    if (node instanceof HTMLElement) {
        return node;
    }

    return undefined;
}

export function elementHide(id: string): void {
    const node = elementFind(id);

    if (node === undefined) {
        return;
    }

    frameShowCancel(node);
    node.classList.remove(CLASS_SHOWN);

    assert(node.isConnected, ATTACHED);
    assert(!node.classList.contains(CLASS_SHOWN), 'a hidden element is not shown');
}

export function elementRemove(id: string): void {
    const node = elementFind(id);

    assert(id.startsWith(ID_PREFIX), ID_NAMED);

    node?.remove();

    assert(node?.isConnected !== true, 'a removed element has left the page');
}

export function elementShow(node: HTMLElement): void {
    assert(node.isConnected, ATTACHED);
    assert(node.id.startsWith(ID_PREFIX), ID_NAMED);

    node.getBoundingClientRect();

    frameShowCancel(node);

    const frame = requestAnimationFrame(() => {
        node.classList.add(CLASS_SHOWN);
    });

    Reflect.set(node, FRAME_SHOW_KEY, frame);
}

export function nodeOf<Tag extends keyof HTMLElementTagNameMap>(
    tag: Tag,
    shape: NodeShape,
): HTMLElementTagNameMap[Tag] {
    assert(tag.length > 0, TAG_NAMED);
    assert(shape.text === undefined || shape.children === undefined, SHAPE_ONE);

    const node = document.createElement(tag);

    if (shape.classes !== undefined) {
        node.setAttribute('class', shape.classes);
    }

    if (shape.id !== undefined) {
        node.id = shape.id;
    }

    if (shape.text !== undefined) {
        node.textContent = textOf(shape.text);
    }

    node.append(...shape.children ?? []);

    assert(node.tagName.toLowerCase() === tag, 'a built node is of the tag asked for');

    return node;
}

export function nodesOfText<Tag extends keyof HTMLElementTagNameMap>(
    tag: Tag,
    shape: NodeShape,
): readonly HTMLElementTagNameMap[Tag][] {
    assert(tag.length > 0, TAG_NAMED);
    assert(shape.children === undefined, SHAPE_ONE);

    if (textOf(shape.text).length === 0) {
        return [];
    }

    const node = nodeOf(tag, shape);

    assert(node.textContent.length > 0, 'a node of text carries its text');

    return [node];
}

export function pixels(value: number): string {
    assert(Number.isFinite(value), PIXELS_FINITE);
    assert(Math.abs(value) <= PIXELS_MAX, PIXELS_SANE);

    return `${String(value)}px`;
}

export function textOf(value: Printable): string {
    return String(value ?? '');
}


function frameShowCancel(node: HTMLElement): void {
    assert(node.isConnected, ATTACHED);
    assert(node.id.startsWith(ID_PREFIX), ID_NAMED);

    const frame: unknown = Reflect.get(node, FRAME_SHOW_KEY);

    if (typeof frame === 'number') {
        cancelAnimationFrame(frame);
    }
}
