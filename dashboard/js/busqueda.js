// busqueda.js — Búsqueda SECOP (SECOP I + II, 2000-2026) con paginación
document.addEventListener('DOMContentLoaded', () => {

    const LIMIT = 10;

    let _page         = 1;
    let _totalPages   = 1;
    let _loading      = false;
    let _lastQuery    = '';
    let _debounceTimer = null;
    let _knownTotal   = -1;

    const input   = document.getElementById('busqueda-input');
    const btn     = document.getElementById('busqueda-btn');
    const tbody   = document.getElementById('busqueda-tbody');
    const countEl = document.getElementById('busqueda-count');
    const emptyEl = document.getElementById('busqueda-empty');
    const errorEl = document.getElementById('busqueda-error');
    const loader  = document.getElementById('busqueda-loader');
    const pagerEl = document.getElementById('busqueda-pager');

    // ── Helpers ──────────────────────────────────────────────────────────────
    const fmt = (v) => {
        const n = parseFloat(v) || 0;
        if (n >= 1e12) return `$${(n/1e12).toFixed(2)}B`;
        if (n >= 1e9)  return `$${(n/1e9).toFixed(1)}M`;
        if (n >= 1e6)  return `$${(n/1e6).toFixed(0)}M`;
        return `$${n.toLocaleString('es-CO', {maximumFractionDigits:0})}`;
    };

    const estadoBadge = (estado) => {
        if (!estado) return '—';
        const e = estado.toLowerCase();
        const cls = e.includes('ejecut') || e.includes('celebr') ? 'badge-green'
                  : e.includes('terminad') || e.includes('liquid') ? 'badge-orange'
                  : 'badge-red';
        return `<span class="badge ${cls}" style="font-size:0.75em">${escapeHtml(estado)}</span>`;
    };

    const fuenteBadge = (f) => {
        const cls = (f || '').includes('2') ? 'badge-azul' : 'badge-green';
        return `<span class="badge ${cls}" style="font-size:0.75em">${escapeHtml(f || 'SECOP')}</span>`;
    };

    // ── Render filas ─────────────────────────────────────────────────────────
    const renderRows = (rows) => {
        tbody.innerHTML = '';
        rows.forEach(c => {
            const tr = document.createElement('tr');
            const objeto = (c.objeto || '—');
            const objetoCorto = objeto.length > 100 ? objeto.substring(0, 100) + '…' : objeto;
            const safeUrl = typeof safeExternalUrl === 'function' ? safeExternalUrl(c.url) : null;
            tr.innerHTML = `
                <td style="white-space:nowrap">${fuenteBadge(c.fuente)}</td>
                <td class="busqueda-objeto" title="${escapeHtml(objeto)}">${escapeHtml(objetoCorto)}</td>
                <td>${escapeHtml(c.entidad || '—')}</td>
                <td class="mono" style="white-space:nowrap">${escapeHtml(c.nit_entidad || '—')}</td>
                <td>${escapeHtml(c.contratista || '—')}</td>
                <td class="mono" style="white-space:nowrap">${escapeHtml(c.doc_contratista || '—')}</td>
                <td class="mono" style="white-space:nowrap;text-align:right"><strong>${escapeHtml(fmt(c.valor))}</strong></td>
                <td style="white-space:nowrap">${escapeHtml((c.fecha || '—').substring(0,10))}</td>
                <td>${estadoBadge(c.estado)}</td>
                <td style="white-space:nowrap;font-size:0.82em">${escapeHtml(c.depto || '—')}</td>
                <td>${safeUrl
                    ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer" class="detalle-link">Ver →</a>`
                    : '—'}</td>`;
            tbody.appendChild(tr);
        });
    };

    // ── Paginador ────────────────────────────────────────────────────────────
    const renderPager = () => {
        if (!pagerEl) return;
        pagerEl.innerHTML = '';
        if (_totalPages <= 1) return;

        const mkBtn = (label, page, disabled, active) => {
            const b = document.createElement('button');
            b.textContent = label;
            b.className = 'pager-btn' + (active ? ' pager-active' : '');
            b.disabled = disabled;
            if (!disabled) b.addEventListener('click', () => doSearch(_lastQuery, page));
            return b;
        };

        pagerEl.appendChild(mkBtn('←', _page - 1, _page <= 1, false));

        // Páginas visibles: primera, actual±2, última
        const pages = new Set([1, _totalPages]);
        for (let i = Math.max(1, _page - 2); i <= Math.min(_totalPages, _page + 2); i++) pages.add(i);
        let prev = 0;
        [...pages].sort((a,b)=>a-b).forEach(p => {
            if (prev && p - prev > 1) {
                const dots = document.createElement('span');
                dots.textContent = '…';
                dots.className = 'pager-dots';
                pagerEl.appendChild(dots);
            }
            pagerEl.appendChild(mkBtn(p, p, false, p === _page));
            prev = p;
        });

        pagerEl.appendChild(mkBtn('→', _page + 1, _page >= _totalPages, false));
    };

    // ── API ──────────────────────────────────────────────────────────────────
    const doSearch = async (q, page = 1) => {
        if (_loading) return;
        _loading = true;

        tbody.innerHTML = '';
        if (loader) loader.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
        if (errorEl) { errorEl.textContent = ''; errorEl.style.display = 'none'; }
        if (pagerEl) pagerEl.innerHTML = '';

        try {
            const params = new URLSearchParams({ q, page, limit: LIMIT });
            if (page > 1 && _knownTotal >= 0) params.set('known_total', _knownTotal);
            const res  = await fetch(`/api/search?${params}`);
            const data = await res.json();

            if (loader) loader.style.display = 'none';

            if (data.error) {
                if (errorEl) { errorEl.textContent = `⚠ ${data.error}`; errorEl.style.display = 'block'; }
                _loading = false;
                return;
            }

            _page       = data.page;
            _totalPages = data.pages;
            _lastQuery  = q;
            _knownTotal = data.total;

            renderRows(data.results);
            renderPager();

            if (countEl) {
                const prefix = data.approximate ? '~' : '';
                countEl.textContent = q
                    ? `${prefix}${data.total.toLocaleString('es-CO')} resultado${data.total !== 1 ? 's' : ''} · pág ${_page}/${_totalPages}`
                    : `${data.total.toLocaleString('es-CO')} contratos · pág ${_page}/${_totalPages}`;
            }

            if (!data.results.length) {
                if (emptyEl) emptyEl.style.display = 'block';
            }

            window.scrollTo({ top: 0, behavior: 'smooth' });

        } catch (err) {
            console.error(err);
            if (loader) loader.style.display = 'none';
            if (errorEl) { errorEl.textContent = '⚠ Error al conectar con el servidor.'; errorEl.style.display = 'block'; }
        }

        _loading = false;
    };

    // ── Triggers ─────────────────────────────────────────────────────────────
    const triggerSearch = () => {
        const q = input.value.trim();
        _lastQuery = q;
        _knownTotal = -1;
        doSearch(q, 1);
    };

    input.addEventListener('input', () => {
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(triggerSearch, 400);
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { clearTimeout(_debounceTimer); triggerSearch(); }
    });
    if (btn) btn.addEventListener('click', () => { clearTimeout(_debounceTimer); triggerSearch(); });

    doSearch('', 1);
});
