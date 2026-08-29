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
