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
