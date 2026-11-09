import { assert } from '../assert.ts';


const TAG_INPUT = 'INPUT';
const TYPE_DEFAULT = 'text';


export function inputType(element: Element): string {
    assert(element.tagName.length > 0, 'an element has a tag name');
    assert(element.ownerDocument.defaultView !== null, 'an element sits on a live page');

    if (element.tagName !== TAG_INPUT) {
        return '';
    }

    const type: unknown = Reflect.get(element, 'type');

    if (typeof type !== 'string') {
        return TYPE_DEFAULT;
    }

    return type.toLowerCase();
}
