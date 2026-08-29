let install = () => {
    if (window.top !== window.self) {
        return null;
    }

    if (window.__limelight && window.__limelight.styleNode.isConnected) {
        return window.__limelight;
    }

    let root = document.documentElement;
    let theme = config.theme;

    root.style.setProperty('--limelight-accent', theme.colorAccent);
    root.style.setProperty('--limelight-spotlight', theme.colorSpotlight);
    root.style.setProperty('--limelight-font', theme.fontFamily);

    let style = document.createElement('style');

    style.textContent = config.css;

    document.head.appendChild(style);

    requestAnimationFrame((stampFirst) => {
        requestAnimationFrame((stampSecond) => {
            if (stampSecond - stampFirst <= 0) {
                root.classList.add('limelight-motionless');
            }
        });
    });

    if (config.controls) {
        controlBuild();
    }

    window.__limelight = apiBuild(style);

    return window.__limelight;
};
