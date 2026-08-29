element => {
    const type = (element.type || '').toLowerCase();
    const checkable = type === 'checkbox' || type === 'radio';
    const labelled = element.labels && element.labels.length ? element.labels[0].innerText : '';
    const value = checkable ? '' : (element.value || '');
    const text = element.innerText
        || labelled
        || value
        || element.getAttribute('aria-label')
        || element.getAttribute('placeholder')
        || '';

    return text.trim().split('\n')[0].slice(0, 80);
}
