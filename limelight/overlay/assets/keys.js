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
