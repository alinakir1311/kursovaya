// GitHub Pages applies the exported catalog filters in the browser.
const filters = document.querySelector('form.filters');
if (filters) {
    const params = new URLSearchParams(location.search);
    for (const input of filters.elements) {
        if (!input.name || !params.has(input.name)) continue;
        if (input.type === 'checkbox') input.checked = params.get(input.name) === '1';
        else input.value = params.get(input.name);
    }
    const value = name => params.get(name) || '';
    const query = value('q').trim().toLocaleLowerCase('ru');
    const grid = document.querySelector('.product-grid, .bundle-grid');
    const cards = [...grid.querySelectorAll('article')];
    const validPrice = name => {
        const number = Number(value(name));
        return value(name) && Number.isFinite(number) && number >= 0 && number <= 99999999;
    };
    const visible = cards.filter(({dataset: data}) => {
        const price = Number(data.price);
        return (!query || data.name?.toLocaleLowerCase('ru').includes(query))
            && (!value('category') || data.category === value('category'))
            && (!value('brand') || data.brand === value('brand'))
            && (!value('purpose') || data.purpose === value('purpose'))
            && (!validPrice('min') || price >= Number(value('min')))
            && (!validPrice('max') || price <= Number(value('max')))
            && (!validPrice('budget') || price <= Number(value('budget')))
            && (!value('available') || Number(data.stock) > 0);
    });
    const sort = value('sort');
    if (sort === 'name') {
        visible.sort((a, b) => a.dataset.name.localeCompare(b.dataset.name, 'ru'));
    }
    if (sort === 'price' || sort === '-price') {
        const direction = sort === 'price' ? 1 : -1;
        visible.sort((a, b) => direction * (Number(a.dataset.price) - Number(b.dataset.price)));
    }
    grid.replaceChildren(...visible);
    if (!visible.length) {
        const empty = document.createElement('p');
        empty.className = 'empty';
        empty.textContent = 'Ничего не найдено. Попробуйте изменить фильтры.';
        grid.append(empty);
    }
    if (grid.matches('.product-grid')) {
        document.querySelector('.filters + .muted').textContent = 'Найдено товаров: ' + visible.length;
    }
}
