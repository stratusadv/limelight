(element, point) => {
    const found = document.elementFromPoint(point.x, point.y);

    if (found === null) {
        return false;
    }

    if (element !== found && !element.contains(found)) {
        return false;
    }

    const control = found.closest('button, input, select, textarea');

    return control === null || control.disabled !== true;
}
