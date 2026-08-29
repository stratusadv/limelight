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
