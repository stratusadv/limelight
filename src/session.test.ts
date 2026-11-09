import { afterEach, test } from 'node:test';
import { doesNotThrow, equal, throws } from 'node:assert/strict';

import { sessionRead, sessionWrite } from './session.ts';
import { AssertionError } from './assert.ts';


const KEY = 'limelight-test';


afterEach(() => {
    Reflect.deleteProperty(globalThis, 'sessionStorage');
});

test('sessionRead returns what sessionWrite stored', () => {
    storageServe(new Map());

    sessionWrite({ key: KEY, value: 'stored' });

    equal(sessionRead(KEY), 'stored');
});

test('sessionRead answers undefined for a key never stored', () => {
    storageServe(new Map());

    equal(sessionRead(KEY), undefined);
});

test('sessionRead answers undefined when the page refuses storage', () => {
    storageRefuse(new DOMException('refused', 'SecurityError'));

    equal(sessionRead(KEY), undefined);
});

test('sessionWrite drops the write when the page refuses storage', () => {
    storageRefuse(new DOMException('full', 'QuotaExceededError'));

    doesNotThrow(() => {
        sessionWrite({ key: KEY, value: 'stored' });
    });
});

test('sessionRead lets a programmer error through', () => {
    storageRefuse(new TypeError('a bug, not a refusal'));

    throws(
        () => {
            sessionRead(KEY);
        },
        TypeError,
    );
});

test('sessionWrite lets a programmer error through', () => {
    storageRefuse(new TypeError('a bug, not a refusal'));

    throws(
        () => {
            sessionWrite({ key: KEY, value: 'stored' });
        },
        TypeError,
    );
});

test('sessionRead refuses a key outside the limelight prefix', () => {
    storageServe(new Map());

    throws(
        () => {
            sessionRead('other');
        },
        AssertionError,
    );
});


function storageRefuse(error: unknown): void {
    Object.defineProperty(globalThis, 'sessionStorage', {
        configurable: true,
        get: (): never => {
            throw error;
        },
    });
}

function storageServe(entries: Map<string, string>): void {
    Object.defineProperty(globalThis, 'sessionStorage', {
        configurable: true,
        value: {
            getItem: (key: string): string | undefined => entries.get(key),
            setItem: (key: string, value: string): void => {
                entries.set(key, value);
            },
        },
    });
}
