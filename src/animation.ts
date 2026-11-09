import { assert } from './assert.ts';


export interface Settle {
    readonly ms: number;
}


const ANIMATION_COUNT_MAX = 100_000;
const DELAY_MS_MAX = 2_147_483_647;
const FEW = 'a page runs a bounded number of animations';
const LIVE = 'a settle reads a live page';
const SELECTOR_OVERLAY = '[id^="limelight-"]';
const SETTLE_BOUNDED = 'a settle waits no longer than a timer can count';
const SETTLE_MS_DEFAULT = 2000;
const SETTLE_POSITIVE = 'a settle waits a positive time';


export async function animationsSettle(options: Settle | null | undefined): Promise<number> {
    const expired = delay(settleMsOf(options?.ms ?? 0));
    const blocking = animationsBlocking();

    await Promise.race([animationsFinished(blocking), expired]);

    assert(blocking.length <= ANIMATION_COUNT_MAX, FEW);
    assert(document.defaultView !== null, LIVE);

    return blocking.length;
}


function animationsBlocking(): readonly Animation[] {
    assert(document.defaultView !== null, LIVE);

    const blocking = document.getAnimations().filter((animation) => isAnimationBlocking(animation));

    assert(blocking.length <= ANIMATION_COUNT_MAX, FEW);

    return blocking;
}

async function animationsFinished(animations: readonly Animation[]): Promise<void> {
    await Promise.allSettled(animations.map(async (animation) => animation.finished));
    await frameNext();
    await frameNext();

    assert(animations.length <= ANIMATION_COUNT_MAX, FEW);
    assert(document.defaultView !== null, LIVE);
}

async function delay(ms: number): Promise<void> {
    assert(ms > 0, SETTLE_POSITIVE);
    assert(ms <= DELAY_MS_MAX, SETTLE_BOUNDED);

    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

async function frameNext(): Promise<void> {
    await new Promise((resolve) => {
        requestAnimationFrame(resolve);
    });

    assert(document.defaultView !== null, LIVE);
    assert(document.getAnimations().length <= ANIMATION_COUNT_MAX, FEW);
}

function isAnimationBlocking(animation: Animation): boolean {
    assert(document.defaultView !== null, LIVE);

    if (animation.playState !== 'running') {
        return false;
    }

    const { effect } = animation;

    if (!(effect instanceof KeyframeEffect)) {
        return false;
    }

    if (effect.getComputedTiming().iterations === Infinity) {
        return false;
    }

    const { target } = effect;

    if (target === null) {
        return false;
    }

    assert(target.isConnected, 'a running animation in the document targets the document');

    return target.closest(SELECTOR_OVERLAY) === null;
}

function settleMsOf(ms: number): number {
    assert(Number.isFinite(ms), SETTLE_POSITIVE);
    assert(ms >= 0, SETTLE_POSITIVE);

    if (ms === 0) {
        return SETTLE_MS_DEFAULT;
    }

    return ms;
}
