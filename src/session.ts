import { assert } from './assert.ts';


export interface SessionEntry {
    readonly key: string;
    readonly value: string;
}


const KEY_PREFIX = 'limelight-';
const KEY_PREFIXED = 'a session key belongs to limelight';
const KEY_SHORT = 'a session key is one short name';
const KEY_LENGTH_MAX = 64;
const VALUE_LENGTH_MAX = 256;


export function sessionRead(key: string): string | undefined {
    let value: string | null | undefined;

    assert(key.startsWith(KEY_PREFIX), KEY_PREFIXED);
    assert(key.length <= KEY_LENGTH_MAX, KEY_SHORT);

    try {
        value = sessionStorage.getItem(key);
    } catch (error: unknown) {
        if (!isRefused(error)) {
            throw error;
        }
    }

    return value ?? undefined;
}

export function sessionWrite(entry: SessionEntry): void {
    assert(entry.key.startsWith(KEY_PREFIX), KEY_PREFIXED);
    assert(entry.key.length <= KEY_LENGTH_MAX, KEY_SHORT);
    assert(entry.value.length <= VALUE_LENGTH_MAX, 'a session value is one short reading');

    try {
        sessionStorage.setItem(entry.key, entry.value);
    } catch (error: unknown) {
        if (!isRefused(error)) {
            throw error;
        }
    }
}


function isRefused(error: unknown): boolean {
    assert(error !== undefined, 'a failed storage call throws an error');

    return error instanceof DOMException;
}
