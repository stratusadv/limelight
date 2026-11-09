import { assert } from '../assert.ts';


const QUERY = '(prefers-color-scheme: dark)';


export function isColorSchemeDark(): boolean {
    assert(document.defaultView !== null, 'a color scheme belongs to a live page');

    const query = matchMedia(QUERY);

    assert(query.media.length > 0, 'the browser understands the query');

    return query.matches;
}
