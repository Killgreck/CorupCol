// carruseles.js — Tabla carrusel + timelines inline + descarga CSV
document.addEventListener('DOMContentLoaded', () => {

    const COLS = ['display_name', 'c.doc_id', 'entidades_distintas', 'total_contratos', 'total_valor_b'];

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
        const tbody = document.querySelector('#table-carrusel tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const maxVal = Math.max(...data.map(d => parseFloat(d.total_valor_b) || 0));

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

            if (row['c.doc_id']) {
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
                    title.textContent = `Línea de Tiempo: ${row.display_name} (NIT: ${row['c.doc_id']})`;
                    const canvas = document.createElement('canvas');
                    container.append(title, canvas);
                    wrapper.appendChild(container);
                    chartTd.appendChild(wrapper);
                    chartTr.appendChild(chartTd);
                    tr.after(chartTr);
                    requestAnimationFrame(() => wrapper.classList.add('expanded'));
                    setTimeout(() => renderTimelineGraph(canvas, row['c.doc_id']), 320);
                });
            }
            tbody.appendChild(tr);
        });

        setupTableSorting('table-carrusel', data, COLS, true, renderTable);
    };

    // Descarga CSV
    const btn = document.getElementById('btn-download');
    if (btn) {
        btn.addEventListener('click', async () => {
            btn.innerHTML = '<span class="btn-icon">⏳</span> Generando…';
            btn.disabled = true;
            try {
                const data = await fetchDashboardJSON('carrusel.json');
                const keys = ['display_name','c.doc_id','entidades_distintas','total_contratos','total_valor','total_valor_b'];
                const csv  = keys.join(',') + '\n' + data.map(obj =>
                    keys.map(k => { let c = String(obj[k] ?? '').replace(/"/g,'""'); return /("|,|\n)/.test(c) ? `"${c}"` : c; }).join(',')
                ).join('\n');
                const zip = new JSZip();
                zip.file('carruseles.csv', csv);
                const blob = await zip.generateAsync({ type: 'blob' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `CorupCol_Carruseles_${new Date().toISOString().split('T')[0]}.zip`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
                btn.innerHTML = '<span class="btn-icon">✅</span> ¡Descargado!';
                setTimeout(() => { btn.innerHTML = '<span class="btn-icon">📦</span> Descargar CSV'; btn.disabled = false; }, 3000);
            } catch (err) {
                console.error(err);
                btn.innerHTML = '<span class="btn-icon">❌</span> Error'; btn.disabled = false;
            }
        });
    }

    const init = async () => {
        try {
            const [carrusel, timelines] = await Promise.all([
                fetchDashboardJSON('carrusel.json'),
                fetchDashboardJSON('timelines.json').catch(() => null)
            ]);
            if (timelines) window._timelines = timelines;
            renderTable(carrusel);
        } catch (e) {
            console.error('Error cargando carruseles:', e);
        }
    };

    init();
});
