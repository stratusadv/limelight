import { assert } from '../assert.ts';


export function selectOptionLabels(element: Element): readonly string[] {
    assert(element.tagName.length > 0, 'an element has a tag name');
    assert(element.ownerDocument.defaultView !== null, 'an element sits on a live page');

    if (element instanceof HTMLSelectElement) {
        return [...element.options].map((option) => option.label);
    }

    return [];
}
