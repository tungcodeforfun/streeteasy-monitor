document.addEventListener('DOMContentLoaded', function () {

    new TomSelect('#areas', {
        hidePlaceholder: true,
        plugins: [
            'remove_button',
            'clear_button',
            'optgroup_columns',
        ],
        maxOptions: null,
    });

    new TomSelect('#amenities', {
        hidePlaceholder: true,
        plugins: [
            'remove_button',
            'clear_button',
        ],
    });

    const form = document.querySelector('.needs-validation');
    form.addEventListener('submit', function (event) {
        if (form.checkValidity() === false) {
            event.preventDefault();
            event.stopPropagation();
        }
        form.classList.add('was-validated');
    }, false);

    // Sortable table columns
    initSortableTable();
});

function initSortableTable() {
    document.querySelectorAll('.sortable').forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => sortTable(header));
    });
}

function sortTable(header) {
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const colIndex = Array.from(header.parentNode.children).indexOf(header);
    const type = header.dataset.type || 'string';

    // Toggle sort direction
    const isAsc = header.classList.contains('sorted-asc');

    // Clear all sort indicators
    header.parentNode.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const icon = th.querySelector('i');
        if (icon) icon.remove();
    });

    const direction = isAsc ? 'desc' : 'asc';
    header.classList.add(`sorted-${direction}`);

    const icon = document.createElement('i');
    icon.className = direction === 'asc' ? 'bi bi-caret-up-fill ms-1' : 'bi bi-caret-down-fill ms-1';
    header.appendChild(icon);

    rows.sort((a, b) => {
        const aVal = a.children[colIndex]?.dataset.value || '';
        const bVal = b.children[colIndex]?.dataset.value || '';

        let comparison = 0;
        if (type === 'number') {
            comparison = (parseFloat(aVal) || 0) - (parseFloat(bVal) || 0);
        } else if (type === 'date') {
            comparison = new Date(aVal) - new Date(bVal);
        } else {
            comparison = aVal.localeCompare(bVal);
        }

        return direction === 'asc' ? comparison : -comparison;
    });

    rows.forEach(row => tbody.appendChild(row));

    // Update row numbers
    rows.forEach((row, i) => {
        row.children[0].textContent = i + 1;
    });
}

// Re-init sorting after HTMX swaps
document.body.addEventListener('htmx:afterSwap', function() {
    initSortableTable();
});
