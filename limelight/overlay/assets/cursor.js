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

            x = inverse * inverse * xStart
                + 2 * inverse * progress * xControl
                + progress * progress * xOvershoot;
            y = inverse * inverse * yStart
                + 2 * inverse * progress * yControl
                + progress * progress * yOvershoot;
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
