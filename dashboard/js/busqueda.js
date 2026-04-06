// busqueda.js — Búsqueda especial: tabla infinita por keyword o NIT
document.addEventListener('DOMContentLoaded', () => {
    let _allData = [];
    let _filtered = [];
    let _page    = 0;
    const PAGE   = 25;

    const tbody    = document.getElementById('busqueda-tbody');
    const loader   = document.getElementById('busqueda-loader');
    const input    = document.getElementById('busqueda-input');
    const countEl  = document.getElementById('busqueda-count');
    const emptyEl  = document.getElementById('busqueda-empty');

    const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    // ── Helpers de presentación ─────────────────────────────────────────────
    const getName = (item) => {
        if (item._type === 'Carrusel')  return item.display_name || '—';
        if (item._type === 'Nepotismo') return item.display_name || item._nombre_contratista_display || item._nombre_contratista || '—';
        const cn = item.contratista_nombre || item.contratista || '';
        return cn && !cn.startsWith('Contratista (DOC') ? cn : (item['ct.id'] || '—');
    };
    const getNIT = (item) => {
        if (item._type === 'Carrusel')  return item['c.doc_id'] || '—';
        if (item._type === 'Nepotismo') {
            const ordenador = item['p.doc_id'] ? `CC ${item['p.doc_id']}` : '';
            const contratista = item['c.doc_id'] ? `NIT ${item['c.doc_id']}` : '';
            return [contratista, ordenador].filter(Boolean).join(' / ') || '—';
        }
        return item['ct.id'] || '—';
    };
    const getDesc = (item) => {
        if (item._type === 'Carrusel') {
            return `Contratista con ${item.entidades_distintas || 0} entidades y ${item.total_contratos || 0} contratos acumulados.`;
        }
        if (item._type === 'Nepotismo') {
            const ordenador = item['p.nombre_display'] || item['p.nombre'] || '—';
            return `Contratista recurrente de ${ordenador}; ${item.contratos_juntos || 0} contratos juntos.`;
        }
        const en = item.entidad_nombre || item.entidad || '';
        const entidad = en && !en.startsWith('Entidad (NIT') ? en : 'Sin entidad';
        const dias = item['ct.dias_adicionados'] || item.dias_prorroga || 0;
        const objeto = item['ct.objeto'] || item.objeto || 'Objeto no disponible';
        return `${objeto} · Entidad: ${entidad} · ${parseInt(dias, 10).toLocaleString('es-CO')} días prórroga`;
    };
    const getValor = (item) => {
        if (item._type === 'Carrusel')  return parseFloat(item.total_valor_b) || 0;
        if (item._type === 'Nepotismo') return parseFloat(item.valor_total_b) || 0;
        return (parseFloat(item['ct.valor']) || 0) / 1e12;
    };
    const getDrillId = (item) => {
        if (item._type === 'Carrusel') return item['c.doc_id'] || '';
        if (item._type === 'Nepotismo') return item['c.doc_id'] || item['p.doc_id'] || '';
        return item['c.doc_id'] || item.doc_id || '';
    };

    const BADGE = { Carrusel: 'badge-carrusel', Nepotismo: 'badge-nepotismo', Sobrecosto: 'badge-sobrecosto' };
    const ICON  = { Carrusel: '🔄', Nepotismo: '👥', Sobrecosto: '⏱️' };

    // ── Render filas ────────────────────────────────────────────────────────
    const renderRows = (items) => {
        items.forEach(item => {
            const nit    = getNIT(item);
            const drillId = getDrillId(item);
            const valorB = getValor(item);
            const tr     = document.createElement('tr');
            tr.dataset.nit = drillId;
            tr.innerHTML = `
                <td><span class="badge ${BADGE[item._type] || ''}">${ICON[item._type] || ''} ${escapeHtml(item._type)}</span></td>
                <td><strong>${escapeHtml(getName(item))}</strong></td>
                <td class="mono" style="white-space:nowrap">${escapeHtml(nit)}</td>
                <td style="font-size:0.85em;color:var(--text-secondary)">${escapeHtml(getDesc(item))}</td>
                <td class="mono"><strong>$${valorB.toLocaleString('es-CO', { minimumFractionDigits: 2 })}B</strong>
                    <div class="valor-usd">${formatUSD(valorB)}</div></td>
                <td>${drillId
                    ? `<button class="btn-secondary btn-sm btn-drill" data-nit="${escapeHtml(drillId)}">Ver contratos</button>`
                    : '<span class="text-secondary" style="font-size:0.8em">Sin NIT</span>'}</td>`;
            tbody.appendChild(tr);
        });
    };

    // ── Scroll infinito ─────────────────────────────────────────────────────
    const loadMore = () => {
        const chunk = _filtered.slice(_page * PAGE, (_page + 1) * PAGE);
        if (!chunk.length) { if (loader) loader.style.display = 'none'; return; }
        renderRows(chunk);
        _page++;
        if (_page * PAGE >= _filtered.length && loader) loader.style.display = 'none';
    };

    if (loader) {
        new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) loadMore();
        }, { rootMargin: '200px' }).observe(loader);
    }

    // ── Búsqueda ────────────────────────────────────────────────────────────
    const performSearch = () => {
        const q = norm(input.value.trim());
        _filtered = q.length < 2
            ? _allData
            : _allData.filter(item => Object.values(item).some(v => norm(v).includes(q)));
        tbody.innerHTML = '';
        _page = 0;
        if (countEl) countEl.textContent = `${_filtered.length.toLocaleString('es-CO')} resultado${_filtered.length !== 1 ? 's' : ''}`;
        if (emptyEl) emptyEl.style.display = (!_filtered.length && q.length >= 2) ? 'block' : 'none';
        if (loader) loader.style.display = _filtered.length > PAGE ? 'block' : 'none';
        loadMore();
    };

    input.addEventListener('input', performSearch);
    document.getElementById('busqueda-btn')?.addEventListener('click', performSearch);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') performSearch(); });

    // ── Drill-down: expandir fila con contratos ─────────────────────────────
    tbody.addEventListener('click', async (e) => {
        const btn = e.target.closest('.btn-drill');
        if (!btn) return;
        const nit = btn.dataset.nit;
        const tr  = btn.closest('tr');

        // Toggle
        const next = tr.nextElementSibling;
        if (next?.classList.contains('drill-row')) {
            next.remove();
            btn.textContent = 'Ver contratos';
            return;
        }

        btn.textContent = '⏳ Cargando…';
        btn.disabled = true;
        const detalles = await fetchDetalleContratos(nit);
        btn.textContent = 'Cerrar ↑';
        btn.disabled = false;

        const drillTr = document.createElement('tr');
        drillTr.className = 'drill-row';
        const drillTd = document.createElement('td');
        drillTd.colSpan = 6;
        drillTd.style.padding = '0';

        if (!detalles) {
            drillTd.innerHTML = '<p class="text-secondary" style="padding:15px">Sin contratos detallados disponibles para este NIT.</p>';
        } else {
            const periodos = Object.keys(detalles).sort();
            if (!periodos.length) {
                drillTd.innerHTML = '<p class="text-secondary" style="padding:15px">Sin contratos registrados.</p>';
            } else {
                const total = periodos.reduce((s, p) => s + detalles[p].length, 0);
                const div = document.createElement('div');
                div.style.cssText = 'padding:12px;background:var(--bg-surface);border-top:1px solid var(--border-color);';
                div.innerHTML = `<div style="margin-bottom:8px">
                    <strong>📋 ${total} contratos en ${periodos.length} períodos — NIT: ${escapeHtml(nit)}</strong>
                </div>`;
                const scroll = document.createElement('div');
                scroll.style.cssText = 'max-height:420px;overflow-y:auto;';
                const table = document.createElement('table');
                table.className = 'detalle-contratos-table';
                table.innerHTML = `<thead><tr>
                    <th>Período</th><th>ID Contrato</th><th>Objeto</th><th>Entidad</th>
                    <th>Valor</th><th>Fecha Firma</th><th>Estado</th><th>Enlace</th>
                </tr></thead>`;
                const tb = document.createElement('tbody');
                periodos.forEach(p => {
                    detalles[p].forEach(c => {
                        const valor = c.valor_del_contrato
                            ? `$${parseFloat(c.valor_del_contrato).toLocaleString('es-CO', { minimumFractionDigits: 0 })}`
                            : '—';
                        const url = c.urlproceso
                            ? `<a href="${escapeHtml(c.urlproceso)}" target="_blank" rel="noopener noreferrer">Ver →</a>`
                            : '—';
                        const tr2 = document.createElement('tr');
                        tr2.innerHTML = `
                            <td class="mono" style="white-space:nowrap">${escapeHtml(p)}</td>
                            <td class="mono" style="white-space:nowrap;font-size:0.8em">${escapeHtml(c.id_contrato || '—')}</td>
                            <td style="font-size:0.85em">${escapeHtml((c.objeto_del_contrato || c.descripcion_del_proceso || '—').substring(0, 80))}</td>
                            <td style="font-size:0.85em">${escapeHtml(c.nombre_entidad || '—')}</td>
                            <td class="mono" style="white-space:nowrap">${escapeHtml(valor)}</td>
                            <td style="white-space:nowrap">${escapeHtml(c.fecha_de_firma || '—')}</td>
                            <td><span class="badge ${c.estado_contrato === 'Celebrado' ? 'badge-green' : 'badge-orange'}">${escapeHtml(c.estado_contrato || '—')}</span></td>
                            <td>${url}</td>`;
                        tb.appendChild(tr2);
                    });
                });
                table.appendChild(tb);
                scroll.appendChild(table);
                div.appendChild(scroll);
                drillTd.appendChild(div);
            }
        }
        drillTr.appendChild(drillTd);
        tr.after(drillTr);
        drillTr.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });

    // ── Init ────────────────────────────────────────────────────────────────
    const init = async () => {
        if (countEl) countEl.textContent = 'Cargando…';
        try {
            const [c, n, s] = await Promise.all([
                fetchDashboardJSON('carrusel.json'),
                fetchDashboardJSON('nepotismo.json'),
                fetchDashboardJSON('sobrecostos.json')
            ]);
            _allData  = [
                ...c.map(i => ({ ...i, _type: 'Carrusel' })),
                ...n.map(i => ({ ...i, _type: 'Nepotismo' })),
                ...s.map(i => ({ ...i, _type: 'Sobrecosto' }))
            ];
            _filtered = _allData;
            if (countEl) countEl.textContent = `${_allData.length.toLocaleString('es-CO')} registros en total`;
            if (loader) loader.style.display = _allData.length > PAGE ? 'block' : 'none';
            loadMore();
        } catch (e) {
            console.error('Error cargando datos de búsqueda:', e);
            if (countEl) countEl.textContent = 'Error al cargar datos';
        }
    };

    init();
});
