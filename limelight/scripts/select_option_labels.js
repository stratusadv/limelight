element => element.tagName === 'SELECT' ? Array.from(element.options).map(option => option.label) : []
