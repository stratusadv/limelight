import { elementFind, nodeOf, pixels } from './dom.ts';
import { sessionRead, sessionWrite } from './session.ts';
import { assert } from './assert.ts';
import { isPointInside } from './geometry.ts';

import type { KeyHud } from './key_hud.ts';
import type { NodeShape } from './dom.ts';
import type { Point } from './geometry.ts';


export type SpeedShift = -1 | 1;

export interface ControlOptions {
    readonly keyHud: KeyHud;
    readonly speedFactor: number;
    readonly stepMode: boolean;
}

export interface ControlSnapshot {
    readonly paused: boolean;
    readonly skip: boolean;
    readonly speedFactor: number;
}

export interface ControlSurface {
    readonly controlCovers: (point: Point) => boolean;
    readonly controlHide: () => void;
    readonly controlPeek: () => ControlSnapshot;
    readonly controlRead: () => ControlSnapshot;
    readonly controlShow: () => void;
}

type ControlKeys = ReadonlyMap<string, () => void>;


const ATTACHED = 'the control bar sits in the page';
const BAR_ID = 'limelight-control';
const BUTTON_FASTER_ID = 'limelight-control-faster';
const BUTTON_PAUSE_ID = 'limelight-control-pause';
const BUTTON_SKIP_ID = 'limelight-control-skip';
const BUTTON_SLOWER_ID = 'limelight-control-slower';
const BUTTON_TURBO_ID = 'limelight-control-turbo';
const CLASS_ENGAGED = 'engaged';
const CLASS_HIDDEN = 'hidden';
const CLASS_SPEED = 'speed';
const ANCHORED = 'the control bar anchors to a measured viewport';
const CONTROL_MARGIN_PX = 32;
const KEY_SKIP = 'ArrowRight';
const KEY_TOGGLE = 'Space';
const KEYS_BOUND = 'the control bar answers the keys it binds';
const LADDER = 'a speed factor stands on the speed ladder';
const LIVE = 'the control bar steers a live page';
const MOVING = 'a speed factor moves the demo forward';
const PAUSE_STATE = 'a pause state is a flag';
const PAUSED_KEY = 'limelight-paused';
const SPEED_FACTOR_DOUBLE = 2;
const SPEED_FACTOR_FIFTY = 50;
const SPEED_FACTOR_HALF = 0.5;
const SPEED_FACTOR_KEY = 'limelight-speed-factor';
const SPEED_FACTOR_ONE_AND_A_HALF = 1.5;
const SPEED_FACTOR_QUADRUPLE = 4;
const SPEED_FACTOR_QUARTER = 0.25;
const SPEED_FACTOR_TEN = 10;
const SPEED_FACTOR_TENTH = 0.1;
const SPEED_FACTOR_TURBO = 1000;
const SPEED_FACTOR_UNIT = 1;
const SPEED_LABEL_ID = 'limelight-control-speed';

const POINTER_EVENT_NAMES = Object.freeze([
    'pointerdown',
    'pointerup',
    'mousedown',
    'mouseup',
    'click',
    'dblclick',
    'contextmenu',
] as const);

const SPEED_FACTORS: readonly number[] = Object.freeze([
    SPEED_FACTOR_TENTH,
    SPEED_FACTOR_QUARTER,
    SPEED_FACTOR_HALF,
    SPEED_FACTOR_UNIT,
    SPEED_FACTOR_ONE_AND_A_HALF,
    SPEED_FACTOR_DOUBLE,
    SPEED_FACTOR_QUADRUPLE,
    SPEED_FACTOR_TEN,
    SPEED_FACTOR_FIFTY,
    SPEED_FACTOR_TURBO,
]);


export class Control {
    #isPaused: boolean;
    #isSkip = false;
    readonly #keyHud: KeyHud;
    #speedFactor: number;
    readonly #stepMode: boolean;

    public constructor(options: ControlOptions) {
        assert(options.speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        this.#isPaused = sessionRead(PAUSED_KEY) === '1';
        this.#keyHud = options.keyHud;
        this.#speedFactor = speedFactorOf(sessionRead(SPEED_FACTOR_KEY), options.speedFactor);
        this.#stepMode = options.stepMode;

        assert(this.#speedFactor > 0, MOVING);
    }

    #barNodes(): readonly HTMLElement[] {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        if (this.#stepMode) {
            return barNodesStep();
        }

        return barNodes();
    }

    #keys(): ControlKeys {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        const skip = (): void => {
            this.#isSkip = true;
        };

        if (this.#stepMode) {
            return new Map([[KEY_SKIP, skip], [KEY_TOGGLE, skip]]);
        }

        return new Map([
            ['ArrowDown', (): void => {
                this.#speedShift(-1);
            }],
            ['ArrowUp', (): void => {
                this.#speedShift(1);
            }],
            ['End', (): void => {
                this.#speedApply(SPEED_FACTOR_TURBO);
            }],
            ['Home', (): void => {
                this.#speedApply(SPEED_FACTOR_TENTH);
            }],
            [KEY_SKIP, skip],
            [KEY_TOGGLE, (): void => {
                this.#pauseToggle();
            }],
        ]);
    }

    #keysWatch(): void {
        const keys = this.#keys();

        assert(keys.has(KEY_SKIP), KEYS_BOUND);
        assert(keys.has(KEY_TOGGLE), KEYS_BOUND);

        document.addEventListener(
            'keydown',
            (event) => {
                if (!isViewerKey(event, this.#keyHud)) {
                    return;
                }

                const action = keys.get(event.code);

                if (action === undefined) {
                    return;
                }

                event.preventDefault();
                event.stopPropagation();

                action();
            },
            { capture: true },
        );
    }

    #pauseToggle(): void {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        this.#isPaused = !this.#isPaused;

        sessionWrite({ key: PAUSED_KEY, value: pausedStored(this.#isPaused) });

        this.#render();
    }

    #render(): void {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        const pauseButton = elementFind(BUTTON_PAUSE_ID);
        const speedLabel = elementFind(SPEED_LABEL_ID);
        const turboButton = elementFind(BUTTON_TURBO_ID);

        if (pauseButton !== undefined) {
            pauseButton.textContent = pauseLabelOf(this.#isPaused);
            pauseButton.classList.toggle(CLASS_ENGAGED, this.#isPaused);
        }

        if (speedLabel !== undefined) {
            speedLabel.textContent = speedLabelOf(this.#speedFactor);
        }

        turboButton?.classList.toggle(CLASS_ENGAGED, this.#speedFactor === SPEED_FACTOR_TURBO);
    }

    #snapshot(): ControlSnapshot {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        return {
            paused: this.#isPaused,
            skip: this.#isSkip,
            speedFactor: this.#speedFactor,
        };
    }

    #speedApply(factor: number): void {
        assert(factor > 0, MOVING);
        assert(SPEED_FACTORS.includes(factor), LADDER);

        this.#speedFactor = factor;

        sessionWrite({ key: SPEED_FACTOR_KEY, value: String(factor) });

        this.#render();
    }

    #speedShift(shift: SpeedShift): void {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        this.#speedApply(speedFactorShifted(this.#speedFactor, shift));
    }

    #turboToggle(): void {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        if (this.#speedFactor === SPEED_FACTOR_TURBO) {
            this.#speedApply(SPEED_FACTOR_UNIT);
        } else {
            this.#speedApply(SPEED_FACTOR_TURBO);
        }
    }

    public barBuild(): void {
        if (elementFind(BAR_ID) !== undefined) {
            return;
        }

        const bar = nodeOf('div', { children: this.#barNodes(), id: BAR_ID });

        document.body.append(bar);

        assert(bar.isConnected, ATTACHED);
        assert(elementFind(BAR_ID) === bar, ATTACHED);
        assert(this.#speedFactor > 0, MOVING);

        barAnchorWatch(bar);
        barContain(bar);

        buttonWire(BUTTON_FASTER_ID, () => {
            this.#speedShift(1);
        });

        buttonWire(BUTTON_PAUSE_ID, () => {
            this.#pauseToggle();
        });

        buttonWire(BUTTON_SKIP_ID, () => {
            this.#isSkip = true;
        });

        buttonWire(BUTTON_SLOWER_ID, () => {
            this.#speedShift(-1);
        });

        buttonWire(BUTTON_TURBO_ID, () => {
            this.#turboToggle();
        });

        this.#keysWatch();
        this.#render();
    }

    public surface(): ControlSurface {
        assert(this.#speedFactor > 0, MOVING);
        assert(document.defaultView !== null, LIVE);

        return {
            controlCovers: (point): boolean => isBarCovering(point),
            controlHide: (): void => {
                elementFind(BAR_ID)?.classList.add(CLASS_HIDDEN);
            },
            controlPeek: (): ControlSnapshot => this.#snapshot(),
            controlRead: (): ControlSnapshot => {
                const snapshot = this.#snapshot();

                this.#isSkip = false;

                return snapshot;
            },
            controlShow: (): void => {
                elementFind(BAR_ID)?.classList.remove(CLASS_HIDDEN);
            },
        };
    }
}


export function speedFactorOf(stored: string | undefined, speedFactorConfigured: number): number {
    assert(speedFactorConfigured > 0, MOVING);
    assert(Number.isFinite(speedFactorConfigured), MOVING);

    const factor = Number(stored ?? 0);

    if (factor === 0) {
        return speedFactorConfigured;
    }

    if (Number.isNaN(factor)) {
        return speedFactorConfigured;
    }

    return factor;
}

export function speedFactorShifted(factor: number, shift: SpeedShift): number {
    assert(factor > 0, MOVING);
    assert(SPEED_FACTORS.length > 0, LADDER);

    const index = speedFactorIndexOf(factor);
    const indexShifted = Math.min(SPEED_FACTORS.length - 1, Math.max(0, index + shift));
    const shifted = SPEED_FACTORS[indexShifted];

    assert(shifted !== undefined, LADDER);

    return shifted;
}

export function speedLabelOf(factor: number): string {
    assert(factor > 0, MOVING);
    assert(Number.isFinite(factor), MOVING);

    if (factor === SPEED_FACTOR_TURBO) {
        return 'Turbo';
    }

    return `${String(factor)}x`;
}


function barAnchor(bar: HTMLElement): void {
    assert(bar.id === BAR_ID, ATTACHED);

    const viewport = viewportVisual();

    assert(Number.isFinite(viewport.width), ANCHORED);

    const scrollbarWidth = window.innerWidth - viewport.width;
    const scrollbarHeight = window.innerHeight - viewport.height;

    bar.style.right = pixels(CONTROL_MARGIN_PX - scrollbarWidth);
    bar.style.bottom = pixels(CONTROL_MARGIN_PX - scrollbarHeight);
}

function barAnchorWatch(bar: HTMLElement): void {
    assert(bar.isConnected, ATTACHED);
    assert(bar.id === BAR_ID, ATTACHED);

    barAnchor(bar);

    const observer = new ResizeObserver(() => {
        barAnchor(bar);
    });

    observer.observe(document.documentElement);

    viewportVisual().addEventListener('resize', () => {
        barAnchor(bar);
    });
}

function barContain(bar: HTMLElement): void {
    assert(bar.isConnected, ATTACHED);
    assert(bar.id === BAR_ID, ATTACHED);

    for (let index = 0; index < POINTER_EVENT_NAMES.length; index += 1) {
        const name = POINTER_EVENT_NAMES[index];

        assert(name !== undefined, 'each pointer event name is listed');

        bar.addEventListener(name, (event) => {
            event.stopPropagation();

            if (name === 'mousedown') {
                event.preventDefault();
            }
        });
    }
}

function barNodes(): readonly HTMLElement[] {
    assert(document.defaultView !== null, LIVE);

    return [
        buttonOf({ id: BUTTON_PAUSE_ID, text: 'Pause' }),
        buttonOf({ id: BUTTON_SLOWER_ID, text: 'Slower' }),
        nodeOf('span', { classes: CLASS_SPEED, id: SPEED_LABEL_ID, text: '1x' }),
        buttonOf({ id: BUTTON_FASTER_ID, text: 'Faster' }),
        buttonOf({ id: BUTTON_TURBO_ID, text: 'Turbo' }),
        buttonOf({ id: BUTTON_SKIP_ID, text: 'Skip' }),
    ];
}

function barNodesStep(): readonly HTMLElement[] {
    assert(document.defaultView !== null, LIVE);

    return [
        nodeOf('span', { classes: CLASS_SPEED, text: 'Step' }),
        buttonOf({ id: BUTTON_SKIP_ID, text: 'Next' }),
    ];
}

function buttonOf(shape: NodeShape): HTMLElement {
    assert(shape.id !== undefined, 'a bar button carries an id');
    assert(shape.text !== undefined, 'a bar button carries a label');

    const button = nodeOf('button', shape);

    button.type = 'button';

    return button;
}

function buttonWire(id: string, handler: () => void): void {
    assert(id.startsWith(BAR_ID), ATTACHED);
    assert(document.defaultView !== null, LIVE);

    const button = elementFind(id);

    if (button === undefined) {
        return;
    }

    button.addEventListener('pointerdown', () => {
        handler();
    });

    button.addEventListener('click', (event) => {
        if (event.detail > 0) {
            return;
        }

        handler();
    });
}

function isBarCovering(point: Point): boolean {
    assert(Number.isFinite(point.x), ANCHORED);
    assert(Number.isFinite(point.y), ANCHORED);

    const bar = elementFind(BAR_ID);

    if (bar === undefined) {
        return false;
    }

    if (bar.classList.contains(CLASS_HIDDEN)) {
        return false;
    }

    return isPointInside(bar.getBoundingClientRect(), point);
}

function isViewerKey(event: KeyboardEvent, keyHud: KeyHud): boolean {
    assert(event.type === 'keydown', KEYS_BOUND);
    assert(document.defaultView !== null, LIVE);

    if (!event.isTrusted) {
        return false;
    }

    if (keyHud.isInputDriven()) {
        return false;
    }

    if (event.metaKey) {
        return false;
    }

    if (event.ctrlKey) {
        return false;
    }

    return !event.altKey;
}

function pauseLabelOf(isPaused: boolean): string {
    assert(typeof isPaused === 'boolean', PAUSE_STATE);

    if (isPaused) {
        return 'Play';
    }

    return 'Pause';
}

function pausedStored(isPaused: boolean): string {
    assert(typeof isPaused === 'boolean', PAUSE_STATE);

    if (isPaused) {
        return '1';
    }

    return '0';
}

function speedFactorIndexOf(factor: number): number {
    assert(factor > 0, MOVING);
    assert(SPEED_FACTORS.includes(SPEED_FACTOR_UNIT), LADDER);

    const index = SPEED_FACTORS.indexOf(factor);

    if (index === -1) {
        return SPEED_FACTORS.indexOf(SPEED_FACTOR_UNIT);
    }

    return index;
}

function viewportVisual(): VisualViewport {
    const viewport = window.visualViewport;

    assert(viewport !== null, ANCHORED);
    assert(document.defaultView !== null, LIVE);

    return viewport;
}
