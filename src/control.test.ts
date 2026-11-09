import { equal, ok } from 'node:assert/strict';
import { test } from 'node:test';

import { speedFactorOf, speedFactorShifted, speedLabelOf } from './control.ts';


test('speedFactorOf prefers the stored factor', () => {
    equal(speedFactorOf('2.5', 1), 2.5);
});

test('speedFactorOf falls back to the configured factor', () => {
    equal(speedFactorOf(undefined, 4), 4);
    equal(speedFactorOf('', 4), 4);
    equal(speedFactorOf('0', 4), 4);
    equal(speedFactorOf('fast', 4), 4);
});

test('speedFactorShifted walks the ladder one rung at a time', () => {
    equal(speedFactorShifted(1, 1), 1.5);
    equal(speedFactorShifted(1, -1), 0.5);
});

test('speedFactorShifted stops at both ends of the ladder', () => {
    equal(speedFactorShifted(0.1, -1), 0.1);
    equal(speedFactorShifted(1000, 1), 1000);
});

test('speedFactorShifted restarts from the unit for a factor off the ladder', () => {
    equal(speedFactorShifted(3, 1), 1.5);
    equal(speedFactorShifted(3, -1), 0.5);
});

test('speedFactorShifted undoes itself away from the ends', () => {
    const rungs = [0.25, 0.5, 1, 1.5, 2, 4, 10, 50];

    for (let index = 0; index < rungs.length; index += 1) {
        const rung = rungs[index];

        ok(rung !== undefined);
        equal(speedFactorShifted(speedFactorShifted(rung, 1), -1), rung);
    }
});

test('speedLabelOf names turbo and prints every other factor', () => {
    equal(speedLabelOf(1000), 'Turbo');
    equal(speedLabelOf(1), '1x');
    equal(speedLabelOf(0.25), '0.25x');
});
