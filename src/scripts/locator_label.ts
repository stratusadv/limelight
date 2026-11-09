import { assert } from '../assert.ts';


const LABEL_LENGTH_MAX = 80;
const LIVE = 'a label is read on a live page';
const NAMED = 'a label belongs to an element';
const TYPE_PASSWORD = 'password';


export function locatorLabel(element: Element): string {
    assert(element.nodeType === Node.ELEMENT_NODE, NAMED);
    assert(element.ownerDocument.defaultView !== null, LIVE);

    const candidates = [
        stringOf(element, 'innerText'),
        labelTextOf(element),
        fieldValueOf(element),
        element.getAttribute('aria-label') ?? '',
        element.getAttribute('placeholder') ?? '',
    ];

    const text = candidates.find((candidate) => candidate.length > 0) ?? '';
    const [lineFirst = ''] = text.trim().split('\n', 1);
    const label = lineFirst.slice(0, LABEL_LENGTH_MAX);

    assert(label.length <= LABEL_LENGTH_MAX, 'a label is one short line');

    return label;
}


function fieldValueOf(element: Element): string {
    assert(element.nodeType === Node.ELEMENT_NODE, NAMED);
    assert(element.ownerDocument.defaultView !== null, LIVE);

    if (isCheckable(element)) {
        return '';
    }

    if (stringOf(element, 'type').toLowerCase() === TYPE_PASSWORD) {
        return '';
    }

    return stringOf(element, 'value');
}

function isCheckable(element: Element): boolean {
    assert(element.nodeType === Node.ELEMENT_NODE, NAMED);
    assert(element.ownerDocument.defaultView !== null, LIVE);

    const type = stringOf(element, 'type').toLowerCase();

    if (type === 'checkbox') {
        return true;
    }

    return type === 'radio';
}

function labelTextOf(element: Element): string {
    assert(element.nodeType === Node.ELEMENT_NODE, NAMED);
    assert(element.ownerDocument.defaultView !== null, LIVE);

    const labels: unknown = Reflect.get(element, 'labels');

    if (!(labels instanceof NodeList)) {
        return '';
    }

    const [label]: readonly unknown[] = [...labels];

    if (label instanceof Element) {
        return stringOf(label, 'innerText');
    }

    return '';
}

function stringOf(element: Element, name: string): string {
    assert(name.length > 0, 'a read names its property');
    assert(element.nodeType === Node.ELEMENT_NODE, NAMED);

    const value: unknown = Reflect.get(element, name);

    if (typeof value === 'string') {
        return value;
    }

    return '';
}
