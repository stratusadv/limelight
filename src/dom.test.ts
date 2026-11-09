import { equal, ok } from 'node:assert/strict';
import { test } from 'node:test';

import { pixels, textOf } from './dom.ts';


test('pixels writes a CSS length', () => {
    equal(pixels(0), '0px');
    equal(pixels(12.5), '12.5px');
    equal(pixels(-3), '-3px');
});

test('textOf prints a value and reads absence as empty', () => {
    const absent: unknown = JSON.parse('null');

    equal(textOf('text'), 'text');
    equal(textOf(0), '0');
    equal(textOf(undefined), '');
    ok(absent === null);
    equal(textOf(absent), '');
});
