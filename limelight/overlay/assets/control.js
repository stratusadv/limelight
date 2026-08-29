let CONTROL_MARGIN_PX = 32;

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
let speedFactorLoad = () =>
    Number(sessionRead('limelight-speed-factor')) || speedFactorConfigured;
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

let controlAnchor = (bar) => {
    let scrollbarWidth = window.innerWidth - window.visualViewport.width;
    let scrollbarHeight = window.innerHeight - window.visualViewport.height;

    bar.style.right = `${CONTROL_MARGIN_PX - scrollbarWidth}px`;
    bar.style.bottom = `${CONTROL_MARGIN_PX - scrollbarHeight}px`;
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
    controlAnchor(bar);

    new ResizeObserver(() => controlAnchor(bar)).observe(document.documentElement);
    window.visualViewport.addEventListener('resize', () => controlAnchor(bar));

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

        node.addEventListener('pointerdown', () => handler());

        node.addEventListener('click', (event) => {
            if (event.detail > 0) {
                return;
            }

            handler();
        });
    }

    let pointerEventNames = [
        'pointerdown',
        'pointerup',
        'mousedown',
        'mouseup',
        'click',
        'dblclick',
        'contextmenu',
    ];

    for (let name of pointerEventNames) {
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
