import { equal, throws } from 'node:assert/strict';
import { test } from 'node:test';

import { assert, AssertionError } from './assert.ts';


test('assert', () => {
    assertWith(true);

    throws(
        () => {
            assertWith(false);
        },
        (error: unknown) => isAssertionError(error, 'the stated reason'),
    );
});

test('AssertionError', () => {
    const named = new AssertionError('named');

    equal(named.name, 'AssertionError');
    equal(named.message, 'named');
});


function assertWith(isSatisfied: boolean): void {
    assert(isSatisfied, 'the stated reason');
}

function isAssertionError(error: unknown, message: string): boolean {
    if (!(error instanceof AssertionError)) {
        return false;
    }

    return error.message === message;
}
