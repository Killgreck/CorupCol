// nepotismo.js — Tabla nepotismo + timelines inline
document.addEventListener('DOMContentLoaded', () => {

    const COLS = ['p.nombre_display', 'p.doc_id', '_nombre_contratista_display', 'contratos_juntos', 'valor_total_b'];

    const appendValueBar = (td, pct) => {
        const container = document.createElement('div');
        container.className = 'value-bar-container js-value-bar-container';
        const fill = document.createElement('div');
        fill.className = 'value-bar js-value-bar-fill';
        fill.style.width = `${pct}%`;
        container.appendChild(fill);
        td.appendChild(container);
    };

    const renderTable = (data) => {
        const tbody = document.querySelector('#table-nepotismo tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const maxVal = Math.max(...data.map(d => parseFloat(d.valor_total_b) || 0));

        data.forEach(row => {
            const tr = document.createElement('tr');
            COLS.forEach((col, idx) => {
                const td = document.createElement('td');
                const val = row[col];
                if (idx === COLS.length - 1) {
                    const n = parseFloat(val) || 0;
                    const pct = maxVal > 0 ? (n / maxVal) * 100 : 0;
                    td.innerHTML = `<strong>$${n.toLocaleString('es-CO', { minimumFractionDigits: 1 })}B COP</strong>
                        <div class="valor-usd">${formatUSD(n)}</div>`;
                    appendValueBar(td, pct);
                } else {
                    td.textContent = val !== undefined && val !== null ? val : 'N/A';
                    if (col.includes('doc_id')) td.className = 'mono';
                }
                tr.appendChild(td);
            });

            if (row['p.doc_id']) {
                tr.classList.add('js-table-row-clickable');
                tr.addEventListener('click', () => {
                    const existing = tr.nextElementSibling;
                    if (existing?.classList.contains('chart-row')) {
                        const w = existing.querySelector('.chart-container-wrapper');
                        w.classList.remove('expanded');
                        setTimeout(() => existing.remove(), 300);
                        return;
                    }
                    document.querySelectorAll('.chart-row').forEach(cr => cr.remove());
                    const chartTr = document.createElement('tr');
                    chartTr.className = 'chart-row';
                    const chartTd = document.createElement('td');
                    chartTd.colSpan = COLS.length;
                    const wrapper = document.createElement('div');
                    wrapper.className = 'chart-container-wrapper';
                    const container = document.createElement('div');
                    container.className = 'chart-container';
                    const title = document.createElement('div');
                    title.className = 'chart-title';
                    title.textContent = `Línea de Tiempo como Ordenador: ${row['p.nombre_display'] || row['p.nombre'] || row['p.doc_id']} (CC: ${row['p.doc_id']})`;
                    const canvas = document.createElement('canvas');
                    container.append(title, canvas);
                    wrapper.appendChild(container);
                    chartTd.appendChild(wrapper);
                    chartTr.appendChild(chartTd);
                    tr.after(chartTr);
                    requestAnimationFrame(() => wrapper.classList.add('expanded'));
                    setTimeout(() => renderTimelineGraph(canvas, row['p.doc_id']), 320);
                });
            }
            tbody.appendChild(tr);
        });

        setupTableSorting('table-nepotismo', data, COLS, true, renderTable);
    };

    const init = async () => {
        try {
            const [nepotismo, timelines] = await Promise.all([
                fetchDashboardJSON('nepotismo.json'),
                fetchDashboardJSON('timelines.json').catch(() => null)
            ]);
            if (timelines) window._timelines = timelines;
            renderTable(nepotismo);
        } catch (e) {
            console.error('Error cargando nepotismo:', e);
        }
    };

    init();
});
