import { assert } from '../assert.ts';


export function scrollIntoView(element: Element): void {
    assert(element.nodeType === Node.ELEMENT_NODE, 'only an element scrolls into view');
    assert(element.ownerDocument.defaultView !== null, 'an element scrolls on a live page');

    element.scrollIntoView({ block: 'center' });
}
