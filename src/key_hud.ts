import { elementBuild, elementHide, elementShow } from './dom.ts';
import { assert } from './assert.ts';


export interface InputDrive {
    readonly ms: number;
}

export interface KeyFlash {
    readonly text: string;
}

export interface KeyHudSurface {
    readonly inputDriveBegin: (drive: InputDrive) => void;
    readonly inputDriveEnd: () => void;
    readonly keyFlash: (flash: KeyFlash) => void;
    readonly keyHudDisable: () => void;
    readonly keyHudEnable: () => void;
}


const BOUNDED = 'the key display holds a bounded tail of text';
const DRIVE_FORWARD = 'a drive window opens forward in time';
const KEY_FLASH_MS = 900;
const KEY_HUD_ID = 'limelight-keys';
const KEY_HUD_LENGTH_MAX = 40;
const LIVE = 'the key display watches a live page';


export class KeyHud {
    #drivenUntilMs = 0;
    #isEnabled = false;
    readonly #onKeyDown = this.#keyDown.bind(this);
    #text = '';

    public constructor() {
        assert(document.defaultView !== null, LIVE);
        assert(this.#text.length === 0, BOUNDED);

        document.addEventListener('keydown', this.#onKeyDown, { capture: true });
    }

    #keyDown(event: KeyboardEvent): void {
        assert(event.type === 'keydown', 'the display reads key presses');
        assert(this.#text.length <= KEY_HUD_LENGTH_MAX, BOUNDED);

        if (!this.#isEnabled) {
            return;
        }

        if (event.key.length !== 1) {
            return;
        }

        this.#text = `${this.#text}${event.key}`.slice(-KEY_HUD_LENGTH_MAX);

        keyHudRender(this.#text);
    }

    public isInputDriven(): boolean {
        assert(this.#drivenUntilMs >= 0, DRIVE_FORWARD);
        assert(this.#text.length <= KEY_HUD_LENGTH_MAX, BOUNDED);

        return performance.now() < this.#drivenUntilMs;
    }

    public surface(): KeyHudSurface {
        assert(this.#drivenUntilMs === 0, DRIVE_FORWARD);
        assert(!this.#isEnabled, 'the display starts disabled');

        return {
            inputDriveBegin: (drive): void => {
                assert(drive.ms >= 0, DRIVE_FORWARD);

                this.#drivenUntilMs = performance.now() + drive.ms;
            },
            inputDriveEnd: (): void => {
                this.#drivenUntilMs = 0;
            },
            keyFlash: (flash): void => {
                keyHudFlash(flash);
            },
            keyHudDisable: (): void => {
                this.#isEnabled = false;
                this.#text = '';

                elementHide(KEY_HUD_ID);
            },
            keyHudEnable: (): void => {
                this.#isEnabled = true;
                this.#text = '';
            },
        };
    }
}


function keyHudFlash(flash: KeyFlash): void {
    assert(document.defaultView !== null, LIVE);
    assert(flash.text.length > 0, 'a flash names its key');

    keyHudRender(flash.text);

    requestAnimationFrame(() => {
        setTimeout(
            () => {
                elementHide(KEY_HUD_ID);
            },
            KEY_FLASH_MS,
        );
    });
}

function keyHudRender(text: string): void {
    const hud = elementBuild(KEY_HUD_ID);

    assert(hud.isConnected, 'the key display sits in the page');
    assert(hud.id === KEY_HUD_ID, BOUNDED);

    hud.textContent = text;

    elementShow(hud);
}
