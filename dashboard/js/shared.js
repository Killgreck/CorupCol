// shared.js — Utilidades compartidas entre todas las páginas del dashboard

const escapeHtml = (str) => {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
};

// ── Carga robusta de datos ─────────────────────────────────────────────────
const dashboardDataCandidates = (path) => {
    const clean = String(path || '').replace(/^\/+/, '').replace(/^data\//, '');
    return [
        `/static_dashboard/data/${clean}`,
        `/dashboard/data/${clean}`,
        `/data/${clean}`
    ];
};

const fetchDashboardJSON = async (path) => {
    let lastError = null;
    for (const url of dashboardDataCandidates(path)) {
        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
            return await res.json();
        } catch (err) {
            lastError = err;
        }
    }
    throw lastError || new Error(`No se pudo cargar ${path}`);
};

// ── Tasa USD ────────────────────────────────────────────────────────────────
let _usdRate = 4200;
let _usdRatePromise = null;

const fetchUSDRate = () => {
    if (_usdRatePromise) return _usdRatePromise;
    _usdRatePromise = fetch('https://open.er-api.com/v6/latest/USD')
        .then(r => r.json())
        .then(data => { if (data.rates?.COP) _usdRate = data.rates.COP; return _usdRate; })
        .catch(() => _usdRate);
    return _usdRatePromise;
};
fetchUSDRate();

const formatUSD = (billonesCOP) => {
    const usd = billonesCOP * 1e12 / _usdRate;
    if (usd >= 1e12) return `≈ USD ${(usd / 1e12).toFixed(2)} T`;
    if (usd >= 1e9)  return `≈ USD ${(usd / 1e9).toFixed(1)} B`;
    if (usd >= 1e6)  return `≈ USD ${(usd / 1e6).toFixed(1)} M`;
    return `≈ USD ${(usd / 1e3).toFixed(0)} K`;
};

// ── Cache de detalle de contratos por NIT ───────────────────────────────────
const _contratoCache = {};

const fetchDetalleContratos = async (nit) => {
    if (_contratoCache[nit] !== undefined) return _contratoCache[nit];
    try {
        _contratoCache[nit] = await fetchDashboardJSON(`contratos/${encodeURIComponent(nit)}.json`);
    } catch (_) {
        _contratoCache[nit] = null;
    }
    return _contratoCache[nit];
};

// ── Tabla de detalle de contratos ───────────────────────────────────────────
const mostrarTablaDetalle = (container, periodoData, periodo, nit) => {
    const prev = container.querySelector('.detalle-contratos-wrapper');
    if (prev) prev.remove();

    if (!periodoData || periodoData.length === 0) {
        const msg = document.createElement('p');
        msg.className = 'detalle-sin-datos';
        msg.textContent = `Sin detalle individual disponible para ${periodo}.`;
        container.appendChild(msg);
        return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'detalle-contratos-wrapper';

    const header = document.createElement('div');
    header.className = 'detalle-contratos-header';
    header.innerHTML = `<span>📋 <strong>${periodoData.length} contratos</strong> en <strong>${periodo}</strong></span>
        <button class="detalle-close-btn" aria-label="Cerrar detalle">&times; Cerrar</button>`;
    header.querySelector('.detalle-close-btn').addEventListener('click', () => wrapper.remove());
    wrapper.appendChild(header);

    const tableWrap = document.createElement('div');
    tableWrap.className = 'detalle-table-scroll';

    const table = document.createElement('table');
    table.className = 'detalle-contratos-table';
    table.innerHTML = `<thead><tr>
        <th>ID Contrato</th><th>Objeto</th><th>Entidad</th><th>Contratista</th>
        <th>Valor (COP)</th><th>Fecha Firma</th><th>Fecha Inicio</th><th>Fecha Fin</th>
        <th>Estado</th><th>Modalidad</th><th>Días Adicionados</th><th>Enlace</th>
    </tr></thead>`;

    const tbody = document.createElement('tbody');
    periodoData.forEach(c => {
        const tr = document.createElement('tr');
        const valor = c.valor_del_contrato
            ? `$${parseFloat(c.valor_del_contrato).toLocaleString('es-CO', { minimumFractionDigits: 0 })}`
            : '—';
        const url = c.urlproceso
            ? `<a href="${escapeHtml(c.urlproceso)}" target="_blank" rel="noopener noreferrer" class="detalle-link">Ver SECOP</a>`
            : '—';
        tr.innerHTML = `
            <td class="mono" style="white-space:nowrap">${escapeHtml(c.id_contrato || '—')}</td>
            <td class="detalle-objeto">${escapeHtml(c.objeto_del_contrato || c.descripcion_del_proceso || '—')}</td>
            <td>${escapeHtml(c.nombre_entidad || '—')}</td>
            <td>${escapeHtml(c.proveedor_adjudicado || '—')}</td>
            <td class="mono" style="white-space:nowrap">${escapeHtml(valor)}</td>
            <td style="white-space:nowrap">${escapeHtml(c.fecha_de_firma || '—')}</td>
            <td style="white-space:nowrap">${escapeHtml(c.fecha_de_inicio_del_contrato || '—')}</td>
            <td style="white-space:nowrap">${escapeHtml(c.fecha_de_fin_del_contrato || '—')}</td>
            <td><span class="badge ${c.estado_contrato === 'Celebrado' ? 'badge-green' : 'badge-orange'}">${escapeHtml(c.estado_contrato || '—')}</span></td>
            <td style="font-size:0.8em">${escapeHtml(c.modalidad_de_contratacion || '—')}</td>
            <td class="mono">${escapeHtml(String(c.dias_adicionados || '0'))}</td>
            <td>${url}</td>`;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tableWrap.appendChild(table);
    wrapper.appendChild(tableWrap);
    container.appendChild(wrapper);
    wrapper.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
};

// ── Timelines globales (cada página los carga si los necesita) ──────────────
window._timelines = window._timelines || {};

const renderTimelineGraph = (canvas, nit) => {
    const data = window._timelines[nit];

    if (!data || data.length === 0) {
        const w = canvas.clientWidth || canvas.offsetWidth || 300;
        const h = canvas.clientHeight || canvas.offsetHeight || 150;
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.font = '14px Inter';
        ctx.fillStyle = '#8b949e';
        ctx.textAlign = 'center';
        ctx.fillText('No hay datos históricos disponibles', w / 2, h / 2);
        return null;
    }

    const labels = data.map(d => d.fecha);
    const values = data.map(d => d.valor_total_b || 0);

    const chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Valor de Contratos (Billones COP)',
                data: values,
                backgroundColor: 'rgba(56, 139, 253, 0.7)',
                borderColor: '#388bfd',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const idx = context.dataIndex;
                            const numC = data[idx] ? data[idx].num_contratos : 0;
                            const val = context.parsed.y;
                            return [
                                `Valor: $${val.toLocaleString('es-CO', { minimumFractionDigits: 3 })}B COP`,
                                `Contratos: ${numC} · Click para ver detalle`
                            ];
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#8b949e' } },
                x: { grid: { display: false }, ticks: { color: '#e6edf3' } }
            },
            onClick: async (event, elements) => {
                if (!elements.length) return;
                const idx = elements[0].index;
                const periodo = labels[idx];
                const modalDetalle = document.getElementById('timeline-modal-detalle');
                const container = modalDetalle && canvas.closest('.timeline-modal-body')
                    ? modalDetalle
                    : (canvas.closest('.chart-container') || canvas.parentElement);
                const detalles = await fetchDetalleContratos(nit);
                mostrarTablaDetalle(container, detalles ? (detalles[periodo] || []) : [], periodo, nit);
            }
        }
    });
    canvas.style.cursor = 'pointer';
    return chart;
};

// ── Ordenamiento de tablas ──────────────────────────────────────────────────
const setupTableSorting = (tableId, data, columns, addValueBar, customRender = null) => {
    document.querySelectorAll(`#${tableId} th[data-sort]`).forEach(th => {
        const newTh = th.cloneNode(true);
        th.parentNode.replaceChild(newTh, th);
        newTh.addEventListener('click', () => {
            const sortKey = newTh.getAttribute('data-sort');
            const isDesc = newTh.classList.contains('sorted-desc');
            document.querySelectorAll(`#${tableId} th`).forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
                const icon = h.querySelector('.sort-icon');
                if (icon) icon.textContent = '↕';
            });
            newTh.classList.add(isDesc ? 'sorted-asc' : 'sorted-desc');
            const icon = newTh.querySelector('.sort-icon');
            if (icon) icon.textContent = isDesc ? '↑' : '↓';
            data.sort((a, b) => {
                let va = a[sortKey], vb = b[sortKey];
                if (!isNaN(parseFloat(va)) && isFinite(va)) {
                    return isDesc ? parseFloat(va) - parseFloat(vb) : parseFloat(vb) - parseFloat(va);
                }
                va = String(va || '').toLowerCase();
                vb = String(vb || '').toLowerCase();
                if (va < vb) return isDesc ? -1 : 1;
                if (va > vb) return isDesc ? 1 : -1;
                return 0;
            });
            if (customRender) customRender(data);
        });
    });
};
