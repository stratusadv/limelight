import {
    elementBuild,
    elementHide,
    elementRemove,
    elementShow,
    nodeOf,
    nodesOfText,
    textOf,
} from './dom.ts';
import { assert } from './assert.ts';

import type { Printable } from './dom.ts';


export interface Caption {
    readonly body?: string;
    readonly step?: string;
    readonly title: string;
}

export interface CardSurface {
    readonly backdropHide: () => void;
    readonly backdropRemove: () => void;
    readonly backdropShow: () => void;
    readonly caption: (caption: Caption) => void;
    readonly captionHide: () => void;
    readonly captionRemove: () => void;
    readonly metrics: (metrics: Metrics) => void;
    readonly metricsHide: () => void;
    readonly metricsRemove: () => void;
    readonly title: (title: Title) => void;
    readonly titleHide: () => void;
    readonly titleRemove: () => void;
}

export interface MetricRow {
    readonly after: Printable;
    readonly before: Printable;
    readonly delta: Printable;
    readonly direction: Printable;
    readonly label: Printable;
    readonly sentiment?: string;
}

export interface Metrics {
    readonly kicker?: string;
    readonly rows: readonly MetricRow[];
    readonly subtitle?: string;
    readonly title: string;
}

export interface Title {
    readonly kicker?: string;
    readonly subtitle?: string;
    readonly title: string;
}


const ARROW = '→';
const ATTACHED = 'a card sits in the page';
const BACKDROP_ID = 'limelight-backdrop';
const CAPTION_ID = 'limelight-caption';
const CELL_COUNT = 5;
const CELLS_COMPLETE = 'a metric row fills each column';
const CLASS_BOX = 'box';
const CLASS_KICKER = 'kicker';
const CLASS_NUMERIC = 'num';
const FILLED = 'a card holds what it was drawn with';
const METRICS_ID = 'limelight-metrics';
const SENTIMENT_FLAT = 'flat';
const TITLE_ID = 'limelight-title';


export const CARD_SURFACE: CardSurface = Object.freeze({
    backdropHide: (): void => {
        elementHide(BACKDROP_ID);
    },
    backdropRemove: (): void => {
        elementRemove(BACKDROP_ID);
    },
    backdropShow: (): void => {
        elementShow(elementBuild(BACKDROP_ID));
    },
    caption: (caption: Caption): void => {
        captionShow(caption);
    },
    captionHide: (): void => {
        elementHide(CAPTION_ID);
    },
    captionRemove: (): void => {
        elementRemove(CAPTION_ID);
    },
    metrics: (metrics: Metrics): void => {
        metricsShow(metrics);
    },
    metricsHide: (): void => {
        elementHide(METRICS_ID);
    },
    metricsRemove: (): void => {
        elementRemove(METRICS_ID);
    },
    title: (title: Title): void => {
        titleShow(title);
    },
    titleHide: (): void => {
        elementHide(TITLE_ID);
    },
    titleRemove: (): void => {
        elementRemove(TITLE_ID);
    },
});


function captionShow(caption: Caption): void {
    const card = elementBuild(CAPTION_ID);

    assert(card.isConnected, ATTACHED);

    card.replaceChildren(
        ...pillsOf(caption.step),
        nodeOf('h3', { text: caption.title }),
        ...nodesOfText('p', { text: caption.body }),
    );

    assert(card.childElementCount > 0, FILLED);
    assert(card.id === CAPTION_ID, ATTACHED);

    elementShow(card);
}

function metricRowOf(row: MetricRow): HTMLElement {
    const direction = textOf(row.direction);
    const sentiment = textOf(row.sentiment);

    const cells = [
        nodeOf('td', { classes: 'metric', text: row.label }),
        nodeOf('td', { classes: `before ${CLASS_NUMERIC}`, text: row.before }),
        nodeOf('td', { classes: 'arrow', text: ARROW }),
        nodeOf('td', { classes: `after ${CLASS_NUMERIC}`, text: row.after }),
        nodeOf('td', { classes: `delta ${CLASS_NUMERIC}`, text: row.delta }),
    ];

    assert(cells.length === CELL_COUNT, CELLS_COMPLETE);

    const classes = `dir-${direction} sentiment-${sentimentOr(sentiment)}`;
    const tableRow = nodeOf('tr', { children: cells, classes });

    assert(tableRow.cells.length === CELL_COUNT, CELLS_COMPLETE);

    return tableRow;
}

function metricsHead(): HTMLElement {
    const cells = [
        nodeOf('th', { text: 'What changed in the system' }),
        nodeOf('th', { classes: CLASS_NUMERIC, text: 'Before' }),
        nodeOf('th', {}),
        nodeOf('th', { classes: CLASS_NUMERIC, text: 'After' }),
        nodeOf('th', { classes: CLASS_NUMERIC, text: 'Delta' }),
    ];

    assert(cells.length === CELL_COUNT, CELLS_COMPLETE);

    const head = nodeOf('thead', { children: [nodeOf('tr', { children: cells })] });

    assert(head.rows.length === 1, 'a metrics table has one heading row');

    return head;
}

function metricsShow(metrics: Metrics): void {
    const card = elementBuild(METRICS_ID);
    const rows = metrics.rows.map((row) => metricRowOf(row));
    const body = nodeOf('tbody', { children: rows });
    const table = nodeOf('table', { children: [metricsHead(), body] });

    assert(card.isConnected, ATTACHED);
    assert(body.rows.length === metrics.rows.length, CELLS_COMPLETE);

    const box = nodeOf('div', {
        children: [
            ...nodesOfText('div', { classes: CLASS_KICKER, text: metrics.kicker }),
            nodeOf('h2', { text: metrics.title }),
            ...nodesOfText('p', { classes: 'sub', text: metrics.subtitle }),
            table,
        ],
        classes: CLASS_BOX,
    });

    card.replaceChildren(box);

    assert(card.childElementCount === 1, FILLED);

    elementShow(card);
}

function pillsOf(step: string | undefined): readonly HTMLElement[] {
    const pills = nodesOfText('span', { classes: 'pill pill-step', text: step })
        .map((pill) => nodeOf('div', { children: [pill], classes: 'pills' }));

    assert(pills.length <= 1, 'a caption carries one step at most');

    return pills;
}

function sentimentOr(sentiment: string): string {
    if (sentiment.length === 0) {
        return SENTIMENT_FLAT;
    }

    return sentiment;
}

function titleShow(title: Title): void {
    const card = elementBuild(TITLE_ID);

    assert(card.isConnected, ATTACHED);

    const box = nodeOf('div', {
        children: [
            ...nodesOfText('div', { classes: CLASS_KICKER, text: title.kicker }),
            nodeOf('h1', { text: title.title }),
            ...nodesOfText('p', { text: title.subtitle }),
        ],
        classes: CLASS_BOX,
    });

    card.replaceChildren(box);

    assert(card.childElementCount === 1, FILLED);
    assert(card.id === TITLE_ID, ATTACHED);

    elementShow(card);
}
