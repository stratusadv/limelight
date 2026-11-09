import { animationsSettle } from './animation.ts';
import { assert } from './assert.ts';
import { CARD_SURFACE } from './cards.ts';
import { Control } from './control.ts';
import { Cursor } from './cursor.ts';
import { KeyHud } from './key_hud.ts';
import { SELECT_SURFACE } from './select.ts';
import { Spot } from './spot.ts';

import type { CardSurface } from './cards.ts';
import type { ControlSurface } from './control.ts';
import type { CursorSurface } from './cursor.ts';
import type { KeyHudSurface } from './key_hud.ts';
import type { SelectSurface } from './select.ts';
import type { Settle } from './animation.ts';
import type { SpotSurface } from './spot.ts';


export interface Overlay
    extends CardSurface,
    ControlSurface,
    CursorSurface,
    KeyHudSurface,
    SelectSurface,
    SpotSurface {
    readonly settle: (options: Settle | null | undefined) => Promise<number>;
    readonly styleNode: HTMLStyleElement;
}

export interface OverlayTheme {
    readonly colorAccent: string;
    readonly colorSpotlight: string;
    readonly fontFamily: string;
}

export interface OverlayConfig {
    readonly controls: boolean;
    readonly css: string;
    readonly speedFactor: number;
    readonly stepMode: boolean;
    readonly theme: OverlayTheme;
}


const CLASS_MOTIONLESS = 'limelight-motionless';
const LIVE = 'the overlay installs into a live page';
const OVERLAY_KEY = '__limelight';
const THEME_FILLED = 'a theme fills each of its fields';


export function install(config: OverlayConfig): Overlay | undefined {
    assert(config.css.length > 0, 'the overlay is installed with its stylesheet');
    assert(config.speedFactor > 0, 'a configured speed factor moves the demo forward');

    if (globalThis.top !== globalThis.self) {
        return undefined;
    }

    const installed = overlayInstalled();

    if (installed !== undefined) {
        return installed;
    }

    themeApply(config.theme);

    const styleNode = styleAttached(config.css);
    const keyHud = new KeyHud();
    const spot = new Spot();
    const control = new Control({ ...config, keyHud });
    const cursor = new Cursor();

    motionlessWatch();

    if (config.controls) {
        control.barBuild();
    }

    const overlay: Overlay = {
        ...CARD_SURFACE,
        ...control.surface(),
        ...cursor.surface(),
        ...keyHud.surface(),
        ...SELECT_SURFACE,
        ...spot.surface(),
        settle: animationsSettle,
        styleNode,
    };

    Reflect.set(globalThis, OVERLAY_KEY, overlay);

    return overlay;
}


function isOverlay(value: unknown): value is Overlay {
    assert(document.defaultView !== null, LIVE);

    if (typeof value !== 'object') {
        return false;
    }

    if (value === null) {
        return false;
    }

    return Reflect.get(value, 'styleNode') instanceof HTMLStyleElement;
}

function motionlessWatch(): void {
    assert(document.defaultView !== null, LIVE);
    assert(document.documentElement.isConnected, LIVE);

    requestAnimationFrame((stampFirst) => {
        requestAnimationFrame((stampSecond) => {
            if (stampSecond <= stampFirst) {
                document.documentElement.classList.add(CLASS_MOTIONLESS);
            }
        });
    });
}

function overlayInstalled(): Overlay | undefined {
    assert(document.defaultView !== null, LIVE);

    const overlay: unknown = Reflect.get(globalThis, OVERLAY_KEY);

    if (!isOverlay(overlay)) {
        return undefined;
    }

    if (!overlay.styleNode.isConnected) {
        return undefined;
    }

    return overlay;
}

function styleAttached(css: string): HTMLStyleElement {
    assert(css.length > 0, 'a stylesheet carries rules');

    const style = document.createElement('style');

    style.textContent = css;

    document.head.append(style);

    assert(style.isConnected, 'the stylesheet sits in the page');
    assert(style.textContent === css, 'the stylesheet carries the rules it was given');

    return style;
}

function themeApply(theme: OverlayTheme): void {
    assert(theme.colorAccent.length > 0, THEME_FILLED);
    assert(theme.colorSpotlight.length > 0, THEME_FILLED);
    assert(theme.fontFamily.length > 0, THEME_FILLED);

    const root = document.documentElement;

    root.style.setProperty('--limelight-accent', theme.colorAccent);
    root.style.setProperty('--limelight-spotlight', theme.colorSpotlight);
    root.style.setProperty('--limelight-font', theme.fontFamily);
}
