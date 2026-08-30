let apiBuild = (styleNode) => ({
    backdropHide: () => {
        elementHide('limelight-backdrop');
    },
    backdropRemove: () => {
        elementRemove('limelight-backdrop');
    },
    backdropShow: () => {
        elementShow(elementBuild('limelight-backdrop'));
    },
    caption: (data) => {
        let card = elementBuild('limelight-caption');
        let step = data.step
            ? `<div class="pills"><span class="pill pill-step">${textEscape(data.step)}</span></div>`
            : '';
        let body = data.body ? `<p>${textEscape(data.body)}</p>` : '';

        card.innerHTML = `${step}<h3>${textEscape(data.title)}</h3>${body}`;

        elementShow(card);
    },
    captionHide: () => {
        elementHide('limelight-caption');
    },
    captionRemove: () => {
        elementRemove('limelight-caption');
    },
    controlCovers: (data) => {
        let bar = document.getElementById('limelight-control');

        if (bar === null || bar.classList.contains('hidden')) {
            return false;
        }

        let rect = bar.getBoundingClientRect();

        return data.x >= rect.left && data.x <= rect.right && data.y >= rect.top && data.y <= rect.bottom;
    },
    controlHide: () => {
        let bar = document.getElementById('limelight-control');

        if (bar !== null) {
            bar.classList.add('hidden');
        }
    },
    controlPeek: () => ({
        paused: controlState.paused,
        skip: controlState.skip,
        speedFactor: controlState.speedFactor,
    }),
    controlRead: () => {
        let snapshot = {
            paused: controlState.paused,
            skip: controlState.skip,
            speedFactor: controlState.speedFactor,
        };

        controlState.skip = false;

        return snapshot;
    },
    controlShow: () => {
        let bar = document.getElementById('limelight-control');

        if (bar !== null) {
            bar.classList.remove('hidden');
        }
    },
    selectHide: () => {
        elementRemove('limelight-select');
    },
    selectMark: (data) => {
        let panel = document.getElementById('limelight-select');

        if (panel === null) {
            return;
        }

        let chosen = panel.children[data.index];

        if (chosen !== undefined) {
            chosen.classList.add('chosen');
        }
    },
    selectShow: (data) => {
        let panel = elementBuild('limelight-select');

        panel.innerHTML = data.options
            .map((label) => `<div class="option">${textEscape(label)}</div>`)
            .join('');

        panel.style.left = `${data.box.x}px`;
        panel.style.top = '0px';
        panel.style.minWidth = `${Math.max(data.box.width, 160)}px`;

        let heightPanel = panel.offsetHeight;
        let topBelow = data.box.y + data.box.height + 4;
        let topAbove = Math.max(8, data.box.y - 4 - heightPanel);
        let top = topBelow + heightPanel <= window.innerHeight - 8 ? topBelow : topAbove;

        panel.style.top = `${top}px`;

        let chosen = panel.children[data.index];

        let scrollTop = chosen.offsetTop - panel.clientHeight / 2 + chosen.offsetHeight / 2;

        panel.scrollTop = Math.max(0, scrollTop);
        elementShow(panel);

        let rect = chosen.getBoundingClientRect();

        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    },
    settle: (data) => {
        let deadlineMs = data && data.ms ? data.ms : 2000;
        let expired = new Promise((resolve) => setTimeout(resolve, deadlineMs));

        let blocking = document.getAnimations().filter(animationBlocks);

        let finished = Promise
            .all(blocking.map((animation) => animation.finished.catch(() => {})))
            .then(() => framesWait(2));

        return Promise.race([finished, expired]).then(() => blocking.length);
    },
    cursorHide: () => {
        elementHide('limelight-cursor');
    },
    cursorMove: (data) => {
        let existing = document.getElementById('limelight-cursor');
        let cursor = existing !== null ? existing : elementBuild('limelight-cursor');

        if (existing === null) {
            let origin = cursorPositionLoad() ?? {
                x: window.innerWidth / 2,
                y: window.innerHeight / 2,
            };

            cursor.style.left = `${origin.x}px`;
            cursor.style.top = `${origin.y}px`;
            cursor.getBoundingClientRect();
        }

        elementShow(cursor);
        cursorPositionStore(data.x, data.y);

        let xStart = parseFloat(cursor.style.left) || 0;
        let yStart = parseFloat(cursor.style.top) || 0;
        let distance = Math.hypot(data.x - xStart, data.y - yStart);
        let target = { x: data.x, y: data.y };

        if (distance < 1) {
            cursorGlide(cursor, target, 0, 0, 0);

            return 0;
        }

        if (data.direct) {
            cursorGlide(cursor, target, data.ms, 0, 0);

            return data.ms;
        }

        let paced = data.ms * (0.44 + 0.032 * Math.sqrt(distance));
        let duration = Math.round(Math.min(data.ms * 2, Math.max(data.ms * 0.5, paced)));
        let bowSign = (data.x - xStart) * (data.y - yStart) >= 0 ? -1 : 1;
        let bow = bowSign * Math.min(distance * 0.12, 48);
        let overshootPx = distance >= 80 ? Math.min(distance * 0.04, 10) : 0;

        cursorGlide(cursor, target, duration, bow, overshootPx);

        return duration;
    },
    cursorPulse: () => {
        let cursor = document.getElementById('limelight-cursor');

        if (cursor !== null) {
            cursor.classList.remove('pulse');
            cursor.getBoundingClientRect();
            cursor.classList.add('pulse');
            setTimeout(() => cursor.classList.remove('pulse'), 450);
        }
    },
    cursorRemove: () => {
        elementRemove('limelight-cursor');
    },
    cursorShow: () => {
        let cursor = document.getElementById('limelight-cursor');

        if (cursor !== null) {
            elementShow(cursor);
        }
    },
    metrics: (data) => {
        let card = elementBuild('limelight-metrics');
        let kicker = data.kicker ? `<div class="kicker">${textEscape(data.kicker)}</div>` : '';
        let subtitle = data.subtitle ? `<p class="sub">${textEscape(data.subtitle)}</p>` : '';

        let rows = data.rows.map((row) => `
            <tr class="dir-${textEscape(row.direction)}
                       sentiment-${textEscape(row.sentiment || 'flat')}">
                <td class="metric">${textEscape(row.label)}</td>
                <td class="before num">${textEscape(row.before)}</td>
                <td class="arrow">&rarr;</td>
                <td class="after num">${textEscape(row.after)}</td>
                <td class="delta num">${textEscape(row.delta)}</td>
            </tr>
        `).join('');

        card.innerHTML = `
            <div class="box">
                ${kicker}
                <h2>${textEscape(data.title)}</h2>
                ${subtitle}
                <table>
                    <thead>
                        <tr>
                            <th>What changed in the system</th>
                            <th class="num">Before</th>
                            <th></th>
                            <th class="num">After</th>
                            <th class="num">Delta</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        `;

        elementShow(card);
    },
    metricsHide: () => {
        elementHide('limelight-metrics');
    },
    metricsRemove: () => {
        elementRemove('limelight-metrics');
    },
    inputDriveBegin: (data) => {
        inputDrivenUntil = performance.now() + data.ms;
    },
    inputDriveEnd: () => {
        inputDrivenUntil = 0;
    },
    keyFlash: (data) => {
        keyHudRender(data.text);
        setTimeout(() => elementHide('limelight-keys'), 900);
    },
    keyHudDisable: () => {
        keyHudState.enabled = false;
        keyHudState.text = '';
        elementHide('limelight-keys');
    },
    keyHudEnable: () => {
        keyHudState.enabled = true;
        keyHudState.text = '';
    },
    spot: (data) => {
        let spot = elementBuild('limelight-spot');

        spot.classList.toggle('nodim', data.dim === false);

        if (data.label) {
            elementBuild('limelight-spot-label');
        } else {
            elementRemove('limelight-spot-label');
        }

        spotAnchor = {
            box: data.box,
            label: data.label,
            scrollX: window.scrollX,
            scrollY: window.scrollY,
        };

        spotPlace(data.box, data.label);
    },
    spotClear: () => {
        spotAnchor = null;

        elementRemove('limelight-spot');
        elementRemove('limelight-spot-label');
    },
    styleNode,
    title: (data) => {
        let title = elementBuild('limelight-title');
        let kicker = data.kicker ? `<div class="kicker">${textEscape(data.kicker)}</div>` : '';
        let subtitle = data.subtitle ? `<p>${textEscape(data.subtitle)}</p>` : '';

        let box = `${kicker}<h1>${textEscape(data.title)}</h1>${subtitle}`;

        title.innerHTML = `<div class="box">${box}</div>`;

        elementShow(title);
    },
    titleHide: () => {
        elementHide('limelight-title');
    },
    titleRemove: () => {
        elementRemove('limelight-title');
    },
});
