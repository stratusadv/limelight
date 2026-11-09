import {
    elementBuild,
    elementFind,
    elementRemove,
    elementShow,
    nodeOf,
    pixels,
} from './dom.ts';
import { assert } from './assert.ts';

import type { Box, Point } from './geometry.ts';


export interface PanelHeights {
    readonly panel: number;
    readonly viewport: number;
}

export interface SelectMark {
    readonly index: number;
}

export interface SelectShow {
    readonly box: Box;
    readonly index: number;
    readonly options: readonly string[];
}

export interface SelectSurface {
    readonly selectHide: () => void;
    readonly selectMark: (mark: SelectMark) => void;
    readonly selectShow: (show: SelectShow) => Point;
}


const CHOSEN_LISTED = 'the chosen option is one of the options drawn';
const CLASS_CHOSEN = 'chosen';
const HALF = 0.5;
const INDEX_WHOLE = 'an option index counts from zero';
const PANEL_EDGE_PX = 8;
const PANEL_GAP_PX = 4;
const PANEL_ID = 'limelight-select';
const PANEL_TOP_FINITE = 'a panel opens on a finite line';
const PANEL_WIDTH_PX_MIN = 160;


export const SELECT_SURFACE: SelectSurface = Object.freeze({
    selectHide: (): void => {
        elementRemove(PANEL_ID);
    },
    selectMark: (mark: SelectMark): void => {
        selectMark(mark);
    },
    selectShow: (show: SelectShow): Point => selectShow(show),
});


export function panelTopOf(box: Box, heights: PanelHeights): number {
    assert(heights.panel >= 0, 'a panel has a height');
    assert(heights.viewport >= 0, 'a viewport has a height');

    const topBelow = box.y + box.height + PANEL_GAP_PX;

    assert(Number.isFinite(topBelow), PANEL_TOP_FINITE);

    if (topBelow + heights.panel <= heights.viewport - PANEL_EDGE_PX) {
        return topBelow;
    }

    const topAbove = Math.max(PANEL_EDGE_PX, box.y - PANEL_GAP_PX - heights.panel);

    assert(Number.isFinite(topAbove), PANEL_TOP_FINITE);

    return topAbove;
}


function optionOf(label: string): HTMLElement {
    const option = nodeOf('div', { classes: 'option', text: label });

    assert(option.childNodes.length <= 1, 'an option holds its label alone');
    assert(option.parentNode === null, 'an option is built detached');

    return option;
}

function selectMark(mark: SelectMark): void {
    assert(Number.isSafeInteger(mark.index), INDEX_WHOLE);
    assert(mark.index >= 0, INDEX_WHOLE);

    elementFind(PANEL_ID)?.children[mark.index]?.classList.add(CLASS_CHOSEN);
}

function selectShow(show: SelectShow): Point {
    assert(Number.isSafeInteger(show.index), INDEX_WHOLE);
    assert(show.index < show.options.length, CHOSEN_LISTED);

    const panel = elementBuild(PANEL_ID);

    panel.replaceChildren(...show.options.map((label) => optionOf(label)));

    panel.style.left = pixels(show.box.x);
    panel.style.top = '0px';
    panel.style.minWidth = pixels(Math.max(show.box.width, PANEL_WIDTH_PX_MIN));

    const heights = { panel: panel.offsetHeight, viewport: window.innerHeight };

    panel.style.top = pixels(panelTopOf(show.box, heights));

    const chosen = panel.children[show.index];

    assert(chosen instanceof HTMLElement, CHOSEN_LISTED);

    const scrollTop = chosen.offsetTop - panel.clientHeight * HALF + chosen.offsetHeight * HALF;

    panel.scrollTop = Math.max(0, scrollTop);

    elementShow(panel);

    const rect = chosen.getBoundingClientRect();

    return { x: rect.left + rect.width * HALF, y: rect.top + rect.height * HALF };
}
