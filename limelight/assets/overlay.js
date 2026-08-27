(config) => {
    if (window.top !== window.self) {
        return;
    }

    if (window.__limelight && window.__limelight.styleNode.isConnected) {
        return;
    }

    let theme = config.theme;

    let style = document.createElement('style');

    style.textContent = `
        :root {
            --limelight-accent: ${theme.colorAccent};
            --limelight-spotlight: ${theme.colorSpotlight};
            --limelight-font: ${theme.fontFamily};
        }
        #limelight-caption, #limelight-spot, #limelight-spot-label, #limelight-title {
            position: fixed;
            z-index: 2147483645;
            pointer-events: none;
            font-family: var(--limelight-font);
        }
        #limelight-backdrop {
            position: fixed;
            inset: 0;
            z-index: 2147483644;
            pointer-events: none;
            background: rgba(8, 11, 18, 0.64);
            opacity: 0;
            transition: opacity .4s ease;
        }
        #limelight-backdrop.show { opacity: 1; }
        #limelight-caption {
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%) scale(0.98);
            max-width: min(940px, 92vw);
            background: rgba(15, 18, 26, 0.95);
            color: #f4f6fb;
            border-left: 6px solid var(--limelight-accent);
            border-radius: 16px;
            padding: 20px 30px;
            box-shadow: 0 22px 70px rgba(0, 0, 0, 0.6);
            opacity: 0;
            transition: opacity .4s ease, transform .4s ease;
        }
        #limelight-caption.show {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        #limelight-caption .pills {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        #limelight-caption .pill {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
            padding: 4px 12px;
            border-radius: 999px;
        }
        #limelight-caption .pill-step { background: #26324a; color: #9cc4ff; }
        #limelight-caption .pill-tag  { background: var(--limelight-accent); color: #08111f; }
        #limelight-caption .pill-q    { background: var(--limelight-spotlight); color: #3a2c00; }
        #limelight-caption .pill-a    { background: #7ee0a8; color: #04301a; }
        #limelight-caption h3 {
            margin: 0 0 8px;
            font-size: 23px;
            font-weight: 700;
            line-height: 1.2;
            color: #f4f6fb;
        }
        #limelight-caption p {
            margin: 0;
            font-size: 16px;
            line-height: 1.55;
            color: #c9d4e6;
        }
        #limelight-spot {
            border-radius: 12px;
            border: 3px solid var(--limelight-spotlight);
            box-shadow: 0 0 0 9999px rgba(8, 11, 18, 0.64),
                        0 0 26px 8px color-mix(in srgb, var(--limelight-spotlight) 85%, transparent);
            transition: top .45s ease, left .45s ease, width .45s ease, height .45s ease;
        }
        #limelight-spot.nodim {
            box-shadow: 0 0 0 4px color-mix(in srgb, var(--limelight-spotlight) 45%, transparent),
                        0 0 24px 8px color-mix(in srgb, var(--limelight-spotlight) 90%, transparent);
        }
        #limelight-spot-label {
            background: var(--limelight-spotlight);
            color: #3a2c00;
            font-weight: 700;
            font-size: 14px;
            padding: 7px 13px;
            border-radius: 9px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
            max-width: 360px;
        }
        #limelight-title {
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            background: radial-gradient(circle at 50% 38%, rgba(20, 28, 44, 0.97), rgba(5, 8, 14, 0.99));
            color: #fff;
            opacity: 0;
            transition: opacity .45s ease;
        }
        #limelight-title.show { opacity: 1; }
        #limelight-title .box { max-width: 82vw; }
        #limelight-title .kicker {
            font-size: 15px;
            letter-spacing: .34em;
            text-transform: uppercase;
            color: #9cc4ff;
            margin-bottom: 20px;
        }
        #limelight-title h1 {
            font-size: 48px;
            font-weight: 800;
            margin: 0 0 18px;
            line-height: 1.1;
            color: #fff;
        }
        #limelight-title p {
            font-size: 21px;
            color: #c9d4e6;
            margin: 0;
            line-height: 1.5;
        }
        #limelight-delta {
            position: fixed;
            inset: 0;
            z-index: 2147483645;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            font-family: var(--limelight-font);
            background: radial-gradient(circle at 50% 36%, rgba(20, 28, 44, 0.97), rgba(5, 8, 14, 0.99));
            opacity: 0;
            transition: opacity .45s ease;
        }
        #limelight-delta.show { opacity: 1; }
        #limelight-delta .box { width: min(980px, 92vw); }
        #limelight-delta .kicker {
            font-size: 14px;
            letter-spacing: .3em;
            text-transform: uppercase;
            color: #9cc4ff;
            margin-bottom: 14px;
            text-align: center;
        }
        #limelight-delta h2 {
            font-size: 34px;
            font-weight: 800;
            color: #fff;
            margin: 0 0 10px;
            text-align: center;
            line-height: 1.15;
        }
        #limelight-delta .sub {
            font-size: 17px;
            color: #c9d4e6;
            margin: 0 auto 26px;
            text-align: center;
            max-width: 760px;
            line-height: 1.5;
        }
        #limelight-delta table { width: 100%; border-collapse: collapse; color: #f4f6fb; }
        #limelight-delta thead th {
            font-size: 12px;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: #7e8aa3;
            font-weight: 700;
            padding: 8px 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.14);
        }
        #limelight-delta thead th.num, #limelight-delta td.num { text-align: right; }
        #limelight-delta tbody td {
            font-size: 20px;
            padding: 15px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        }
        #limelight-delta td.metric { font-weight: 600; }
        #limelight-delta td.before { color: #c9d4e6; }
        #limelight-delta td.arrow { color: #5e6b85; text-align: center; }
        #limelight-delta td.after { font-weight: 700; }
        #limelight-delta td.delta { font-weight: 800; }
        #limelight-delta tr.sentiment-good td.delta { color: #7ee0a8; }
        #limelight-delta tr.sentiment-bad td.delta { color: #ffb86b; }
        #limelight-delta tr.sentiment-flat td.delta { color: #7e8aa3; }
        #limelight-cursor {
            position: fixed;
            z-index: 2147483646;
            pointer-events: none;
            width: 22px;
            height: 22px;
            margin: -11px 0 0 -11px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid rgba(8, 11, 18, 0.85);
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.5);
            opacity: 0;
            transition: opacity .25s ease,
                        transform .18s ease;
        }
        #limelight-cursor.show { opacity: 1; }
        #limelight-cursor.pulse { transform: scale(0.82); }
        #limelight-cursor.pulse::after {
            content: '';
            position: absolute;
            inset: -4px;
            border-radius: 50%;
            border: 3px solid var(--limelight-accent);
            animation: limelight-cursor-pulse .4s ease-out;
        }
        @keyframes limelight-cursor-pulse {
            from { transform: scale(0.5); opacity: 1; }
            to { transform: scale(2.4); opacity: 0; }
        }
        #limelight-select {
            position: fixed;
            z-index: 2147483645;
            pointer-events: none;
            overflow-y: auto;
            scrollbar-width: none;
            max-height: 40vh;
            border-radius: 10px;
            background: rgba(252, 253, 255, 0.98);
            border: 1px solid rgba(8, 11, 18, 0.18);
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
            font-family: var(--limelight-font);
            opacity: 0;
            transition: opacity .15s ease;
        }
        #limelight-select.show { opacity: 1; }
        #limelight-select .option {
            padding: 9px 14px;
            font-size: 15px;
            color: #1c2333;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        #limelight-select .option.chosen {
            background: var(--limelight-accent);
            color: #ffffff;
        }
        #limelight-keys {
            position: fixed;
            left: 50%;
            bottom: 64px;
            transform: translateX(-50%);
            z-index: 2147483646;
            pointer-events: none;
            max-width: min(720px, 90vw);
            padding: 8px 16px;
            border-radius: 10px;
            background: rgba(15, 18, 26, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #f4f6fb;
            font-family: ui-monospace, 'Cascadia Mono', 'Consolas', monospace;
            font-size: 15px;
            letter-spacing: .06em;
            white-space: nowrap;
            overflow: hidden;
            opacity: 0;
            transition: opacity .2s ease;
        }
        #limelight-keys.show { opacity: 1; }
        #limelight-control {
            position: fixed;
            left: calc(100vw - 18px);
            bottom: 18px;
            transform: translateX(-100%);
            z-index: 2147483647;
            display: flex;
            align-items: center;
            gap: 0;
            padding: 0;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(15, 18, 26, 0.92);
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            font-family: var(--limelight-font);
            pointer-events: none;
            opacity: 0.55;
            transition: opacity .25s ease;
        }
        #limelight-control:hover { opacity: 1; }
        #limelight-control.hidden { display: none; }
        #limelight-control button {
            border: none;
            border-radius: 0;
            box-shadow: inset -1px 0 rgba(255, 255, 255, 0.14);
            background: transparent;
            color: #f4f6fb;
            font-family: var(--limelight-font);
            font-size: 12px;
            font-weight: 600;
            line-height: 1;
            padding: 13px 15px;
            cursor: pointer;
            pointer-events: auto;
            align-self: stretch;
        }
        #limelight-control button:last-child { box-shadow: none; }
        #limelight-control button:hover { background: rgba(255, 255, 255, 0.12); }
        #limelight-control button.engaged {
            background: var(--limelight-spotlight);
            border-color: var(--limelight-spotlight);
            color: #3a2c00;
        }
        #limelight-control .speed {
            color: #9cc4ff;
            font-size: 12px;
            font-weight: 700;
            min-width: 58px;
            padding: 0 14px;
            box-shadow: inset -1px 0 rgba(255, 255, 255, 0.14);
            text-align: center;
            align-self: stretch;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    `;

    document.head.appendChild(style);

    requestAnimationFrame((stampFirst) => {
        requestAnimationFrame((stampSecond) => {
            if (stampSecond - stampFirst <= 0) {
                style.textContent += `
                    [id^="limelight-"], [id^="limelight-"]::after {
                        transition: none !important;
                        animation: none !important;
                    }
                `;
            }
        });
    });

    let elementBuild = (id) => {
        let node = document.getElementById(id);

        if (node === null) {
            node = document.createElement('div');
            node.id = id;
            document.body.appendChild(node);
        }

        return node;
    };

    let elementHide = (id) => {
        let node = document.getElementById(id);

        if (node !== null) {
            node.classList.remove('show');
        }
    };

    let elementRemove = (id) => {
        let node = document.getElementById(id);

        if (node !== null) {
            node.remove();
        }
    };

    let elementShow = (node) => {
        requestAnimationFrame(() => node.classList.add('show'));
    };

    let textEscape = (value) => String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');

    let animationTarget = (animation) => {
        let effect = animation.effect;

        if (effect === null || effect === undefined) {
            return null;
        }

        let target = effect.target;

        if (target === null || target === undefined) {
            return null;
        }

        return typeof target.closest === 'function' ? target : target.element ?? null;
    };

    let animationBlocks = (animation) => {
        if (animation.playState !== 'running') {
            return false;
        }

        let effect = animation.effect;
        let timing = effect === null || effect === undefined ? null : effect.getComputedTiming();

        if (timing === null || timing.iterations === Infinity) {
            return false;
        }

        let target = animationTarget(animation);

        if (target === null) {
            return false;
        }

        return target.closest('[id^="limelight-"]') === null;
    };

    let framesWait = (count) => new Promise((resolve) => {
        let step = (remaining) => {
            if (remaining <= 0) {
                resolve();

                return;
            }

            requestAnimationFrame(() => step(remaining - 1));
        };

        step(count);
    });

    let cursorGlideFrame = null;

    let cursorGlideCancel = () => {
        if (cursorGlideFrame !== null) {
            cancelAnimationFrame(cursorGlideFrame);
            cursorGlideFrame = null;
        }
    };

    let minimumJerk = (t) => t * t * t * (10 - 15 * t + 6 * t * t);

    let cursorGlide = (cursor, target, duration, bow, overshootPx) => {
        cursorGlideCancel();

        let xStart = parseFloat(cursor.style.left) || 0;
        let yStart = parseFloat(cursor.style.top) || 0;
        let dx = target.x - xStart;
        let dy = target.y - yStart;
        let distance = Math.hypot(dx, dy);

        if (distance < 1 || duration <= 0) {
            cursor.style.left = `${target.x}px`;
            cursor.style.top = `${target.y}px`;
            return;
        }

        let xControl = xStart + dx / 2 - dy / distance * bow;
        let yControl = yStart + dy / 2 + dx / distance * bow;
        let xOvershoot = target.x + dx / distance * overshootPx;
        let yOvershoot = target.y + dy / distance * overshootPx;
        let settleStart = overshootPx > 0 ? 0.84 : 1;
        let elapsed = 0;
        let stampPrevious = null;

        let step = (now) => {
            if (stampPrevious !== null) {
                let delta = now - stampPrevious;

                if (delta <= 0) {
                    delta = 1000 / 60;
                }

                elapsed += delta;
            }

            stampPrevious = now;

            let t = Math.min(1, elapsed / duration);
            let x = target.x;
            let y = target.y;

            if (t < settleStart) {
                let progress = minimumJerk(t / settleStart);
                let inverse = 1 - progress;

                x = inverse * inverse * xStart + 2 * inverse * progress * xControl + progress * progress * xOvershoot;
                y = inverse * inverse * yStart + 2 * inverse * progress * yControl + progress * progress * yOvershoot;
            } else if (t < 1) {
                let settle = (t - settleStart) / (1 - settleStart);
                let eased = 1 - (1 - settle) * (1 - settle);

                x = xOvershoot + (target.x - xOvershoot) * eased;
                y = yOvershoot + (target.y - yOvershoot) * eased;
            }

            cursor.style.left = `${x}px`;
            cursor.style.top = `${y}px`;

            cursorGlideFrame = t < 1 ? requestAnimationFrame(step) : null;
        };

        cursorGlideFrame = requestAnimationFrame(step);
    };

    let inputDrivenUntil = 0;

    let inputDriven = () => performance.now() < inputDrivenUntil;

    let keyHudState = { enabled: false, text: '' };

    let keyHudRender = (text) => {
        let hud = elementBuild('limelight-keys');

        hud.textContent = text;
        elementShow(hud);
    };

    document.addEventListener('keydown', (event) => {
        if (!keyHudState.enabled) {
            return;
        }

        if (event.key.length !== 1) {
            return;
        }

        keyHudState.text = (keyHudState.text + event.key).slice(-40);
        keyHudRender(keyHudState.text);
    }, true);

    let spotAnchor = null;

    let spotPlace = (box, label) => {
        let spot = document.getElementById('limelight-spot');
        let pad = 8;

        if (spot === null) {
            return;
        }

        spot.style.top = `${box.y - pad}px`;
        spot.style.left = `${box.x - pad}px`;
        spot.style.width = `${box.width + pad * 2}px`;
        spot.style.height = `${box.height + pad * 2}px`;

        let labelNode = document.getElementById('limelight-spot-label');

        if (labelNode !== null && label) {
            let labelLeftMax = window.innerWidth - 368;

            labelNode.textContent = label;
            labelNode.style.top = `${Math.max(8, box.y - pad - 44)}px`;
            labelNode.style.left = `${Math.max(8, Math.min(box.x - pad, labelLeftMax))}px`;
        }
    };

    let spotReposition = () => {
        if (spotAnchor === null) {
            return;
        }

        let box = {
            x: spotAnchor.box.x + (spotAnchor.scrollX - window.scrollX),
            y: spotAnchor.box.y + (spotAnchor.scrollY - window.scrollY),
            width: spotAnchor.box.width,
            height: spotAnchor.box.height,
        };

        spotPlace(box, spotAnchor.label);
    };

    if (window.__limelightSpotReposition) {
        window.removeEventListener('scroll', window.__limelightSpotReposition);
    }

    window.__limelightSpotReposition = spotReposition;
    window.addEventListener('scroll', spotReposition, { passive: true });


    let CONTROL_PRESS_WINDOW_MS = 700;

    let speedFactors = [0.1, 0.25, 0.5, 1, 1.5, 2, 4, 10, 50, 1000];
    let speedFactorTurbo = speedFactors.at(-1);
    let speedFactorConfigured = Number(config.speedFactor) || 1;

    let sessionRead = (key) => {
        try {
            return sessionStorage.getItem(key);
        } catch {
            return null;
        }
    };

    let sessionWrite = (key, value) => {
        try {
            sessionStorage.setItem(key, value);
        } catch {
            return;
        }
    };

    let cursorPositionLoad = () => {
        let raw = sessionRead('limelight-cursor-position');

        if (raw === null) {
            return null;
        }

        let parts = raw.split(',');
        let x = Number(parts[0]);
        let y = Number(parts[1]);

        return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
    };

    let cursorPositionStore = (x, y) => sessionWrite('limelight-cursor-position', `${x},${y}`);

    let pausedLoad = () => sessionRead('limelight-paused') === '1';
    let pausedStore = (paused) => sessionWrite('limelight-paused', paused ? '1' : '0');
    let speedFactorLoad = () => Number(sessionRead('limelight-speed-factor')) || speedFactorConfigured;
    let speedFactorStore = (factor) => sessionWrite('limelight-speed-factor', String(factor));

    let controlState = {
        paused: pausedLoad(),
        skip: false,
        speedFactor: speedFactorLoad(),
    };

    let controlRender = () => {
        let pauseButton = document.getElementById('limelight-control-pause');
        let speedLabel = document.getElementById('limelight-control-speed');
        let turboButton = document.getElementById('limelight-control-turbo');

        if (pauseButton !== null) {
            pauseButton.textContent = controlState.paused ? 'Play' : 'Pause';
            pauseButton.classList.toggle('engaged', controlState.paused);
        }

        if (speedLabel !== null) {
            speedLabel.textContent = controlState.speedFactor === speedFactorTurbo
                ? 'Turbo'
                : `${controlState.speedFactor}x`;
        }

        if (turboButton !== null) {
            turboButton.classList.toggle('engaged', controlState.speedFactor === speedFactorTurbo);
        }
    };

    let controlPauseToggle = () => {
        controlState.paused = !controlState.paused;
        pausedStore(controlState.paused);
        controlRender();
    };

    let controlSkip = () => {
        controlState.skip = true;
    };

    let controlSpeedApply = (factor) => {
        controlState.speedFactor = factor;
        speedFactorStore(factor);
        controlRender();
    };

    let controlSpeedShift = (direction) => {
        let index = speedFactors.indexOf(controlState.speedFactor);

        if (index === -1) {
            index = speedFactors.indexOf(1);
        }

        let indexShifted = Math.min(speedFactors.length - 1, Math.max(0, index + direction));

        controlSpeedApply(speedFactors[indexShifted]);
    };

    let controlTurboToggle = () => {
        controlSpeedApply(controlState.speedFactor === speedFactorTurbo ? 1 : speedFactorTurbo);
    };

    let controlBuild = () => {
        if (document.getElementById('limelight-control') !== null) {
            return;
        }

        let bar = document.createElement('div');

        bar.id = 'limelight-control';
        bar.innerHTML = config.stepMode
            ? `
                <span class="speed">Step</span>
                <button id="limelight-control-skip" type="button">Next</button>
            `
            : `
                <button id="limelight-control-pause" type="button">Pause</button>
                <button id="limelight-control-slower" type="button">Slower</button>
                <span id="limelight-control-speed" class="speed">1x</span>
                <button id="limelight-control-faster" type="button">Faster</button>
                <button id="limelight-control-turbo" type="button">Turbo</button>
                <button id="limelight-control-skip" type="button">Skip</button>
            `;

        document.body.appendChild(bar);

        let clickHandlers = {
            'limelight-control-faster': () => controlSpeedShift(1),
            'limelight-control-pause': () => controlPauseToggle(),
            'limelight-control-skip': () => controlSkip(),
            'limelight-control-slower': () => controlSpeedShift(-1),
            'limelight-control-turbo': () => controlTurboToggle(),
        };

        for (let [id, handler] of Object.entries(clickHandlers)) {
            let node = bar.querySelector(`#${id}`);

            if (node === null) {
                continue;
            }

            let stampPressed = 0;

            node.addEventListener('pointerdown', () => {
                stampPressed = performance.now();

                handler();
            });

            node.addEventListener('click', () => {
                if (performance.now() - stampPressed < CONTROL_PRESS_WINDOW_MS) {
                    return;
                }

                handler();
            });
        }

        for (let name of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click', 'dblclick', 'contextmenu']) {
            bar.addEventListener(name, (event) => {
                event.stopPropagation();

                if (name === 'mousedown') {
                    event.preventDefault();
                }
            });
        }

        let keyActions = config.stepMode
            ? {
                ArrowRight: () => controlSkip(),
                Space: () => controlSkip(),
            }
            : {
                ArrowDown: () => controlSpeedShift(-1),
                ArrowRight: () => controlSkip(),
                ArrowUp: () => controlSpeedShift(1),
                End: () => controlSpeedApply(speedFactorTurbo),
                Home: () => controlSpeedApply(speedFactors[0]),
                Space: () => controlPauseToggle(),
            };

        document.addEventListener('keydown', (event) => {
            if (!event.isTrusted || inputDriven()) {
                return;
            }

            if (event.metaKey || event.ctrlKey || event.altKey) {
                return;
            }

            if (!Object.hasOwn(keyActions, event.code)) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            keyActions[event.code]();
        }, true);

        controlRender();
    };

    if (config.controls) {
        controlBuild();
    }

    window.__limelight = {
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
            let pills = [];

            if (data.step) {
                pills.push(`<span class="pill pill-step">${textEscape(data.step)}</span>`);
            }

            if (data.tag) {
                let pillClass = { a: 'pill-a', q: 'pill-q' }[data.kind] ?? 'pill-tag';

                pills.push(`<span class="pill ${pillClass}">${textEscape(data.tag)}</span>`);
            }

            let pillRow = pills.length ? `<div class="pills">${pills.join('')}</div>` : '';
            let body = data.body ? `<p>${textEscape(data.body)}</p>` : '';

            card.innerHTML = `${pillRow}<h3>${textEscape(data.title)}</h3>${body}`;

            elementShow(card);
        },
        captionHide: () => {
            elementHide('limelight-caption');
        },
        captionRemove: () => {
            elementRemove('limelight-caption');
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

            panel.scrollTop = Math.max(0, chosen.offsetTop - panel.clientHeight / 2 + chosen.offsetHeight / 2);
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
        delta: (data) => {
            let card = elementBuild('limelight-delta');
            let kicker = data.kicker ? `<div class="kicker">${textEscape(data.kicker)}</div>` : '';
            let subtitle = data.subtitle ? `<p class="sub">${textEscape(data.subtitle)}</p>` : '';

            let rows = data.rows.map((row) => `
                <tr class="dir-${textEscape(row.direction)} sentiment-${textEscape(row.sentiment || 'flat')}">
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
        deltaHide: () => {
            elementHide('limelight-delta');
        },
        deltaRemove: () => {
            elementRemove('limelight-delta');
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
        styleNode: style,
        title: (data) => {
            let title = elementBuild('limelight-title');
            let kicker = data.kicker ? `<div class="kicker">${textEscape(data.kicker)}</div>` : '';
            let subtitle = data.subtitle ? `<p>${textEscape(data.subtitle)}</p>` : '';

            title.innerHTML = `<div class="box">${kicker}<h1>${textEscape(data.title)}</h1>${subtitle}</div>`;

            elementShow(title);
        },
        titleHide: () => {
            elementHide('limelight-title');
        },
        titleRemove: () => {
            elementRemove('limelight-title');
        },
    };
}
