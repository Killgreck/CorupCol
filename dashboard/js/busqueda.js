// busqueda.js — Búsqueda SECOP completa (SECOP I + II, 2000-2026)
// Usa el endpoint /api/search que busca en el índice FTS5 SQLite
document.addEventListener('DOMContentLoaded', () => {

    // ── Estado ──────────────────────────────────────────────────────────────
    let _page         = 1;
    let _totalPages   = 1;
    let _loading      = false;
    let _lastQuery    = '';
    let _debounceTimer = null;

    // ── Elementos DOM ────────────────────────────────────────────────────────
    const input     = document.getElementById('busqueda-input');
    const btn       = document.getElementById('busqueda-btn');
    const tbody     = document.getElementById('busqueda-tbody');
    const countEl   = document.getElementById('busqueda-count');
    const emptyEl   = document.getElementById('busqueda-empty');
    const errorEl   = document.getElementById('busqueda-error');
    const loader    = document.getElementById('busqueda-loader');

    // ── Helpers ──────────────────────────────────────────────────────────────
    const fmt = (v) => {
        const n = parseFloat(v) || 0;
        if (n >= 1e12) return `$${(n/1e12).toFixed(2)}B`;
        if (n >= 1e9)  return `$${(n/1e9).toFixed(1)}M`;
        if (n >= 1e6)  return `$${(n/1e6).toFixed(0)}M`;
        return `$${n.toLocaleString('es-CO', {maximumFractionDigits:0})}`;
    };

    const fmtFecha = (s) => {
        if (!s) return '—';
        return s.substring(0, 10);
    };

    const estadoBadge = (estado) => {
        if (!estado) return '—';
        const e = estado.toLowerCase();
        const cls = e.includes('ejecut') || e.includes('celebr') ? 'badge-green'
                  : e.includes('terminad') || e.includes('liquid') ? 'badge-orange'
                  : 'badge-red';
        return `<span class="badge ${cls} js-small-badge">${escapeHtml(estado)}</span>`;
    };

    const fuenteBadge = (f) => {
        const cls = (f || '').includes('2') ? 'badge-azul' : 'badge-green';
        return `<span class="badge ${cls} js-small-badge">${escapeHtml(f || 'SECOP')}</span>`;
    };

    // ── Render de filas ──────────────────────────────────────────────────────
    const renderRows = (rows, append = false) => {
        if (!append) tbody.innerHTML = '';
        if (!rows.length) return;

        rows.forEach(c => {
            const tr = document.createElement('tr');
            const objeto = (c.objeto || '—');
            const objetoCorto = objeto.length > 100 ? objeto.substring(0, 100) + '…' : objeto;
            const safeUrl = typeof safeExternalUrl === 'function' ? safeExternalUrl(c.url) : null;
            tr.innerHTML = `
                <td class="js-nowrap">${fuenteBadge(c.fuente)}</td>
                <td class="busqueda-objeto" title="${escapeHtml(objeto)}">${escapeHtml(objetoCorto)}</td>
                <td>${escapeHtml(c.entidad || '—')}</td>
                <td class="mono js-nowrap">${escapeHtml(c.nit_entidad || '—')}</td>
                <td>${escapeHtml(c.contratista || '—')}</td>
                <td class="mono js-nowrap">${escapeHtml(c.doc_contratista || '—')}</td>
                <td class="mono js-nowrap js-right"><strong>${escapeHtml(fmt(c.valor))}</strong></td>
                <td class="js-nowrap">${escapeHtml(fmtFecha(c.fecha))}</td>
                <td>${estadoBadge(c.estado)}</td>
                <td class="js-nowrap js-small">${escapeHtml(c.depto || '—')}</td>
                <td>${safeUrl
                    ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer" class="detalle-link">Ver →</a>`
                    : '—'}</td>`;
            tbody.appendChild(tr);
        });
    };

    // ── Llamada al API ───────────────────────────────────────────────────────
    const doSearch = async (q, page = 1, append = false) => {
        if (_loading) return;
        _loading = true;

        if (!append) {
            tbody.innerHTML = '';
            if (loader) loader.style.display = 'block';
        }
        if (emptyEl) emptyEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';

        try {
            const params = new URLSearchParams({ q, page, limit: 50 });
            const res    = await fetch(`/api/search?${params}`);
            const data   = await res.json();

            if (data.error) {
                if (errorEl) {
                    errorEl.textContent = `⚠ ${data.error}`;
                    errorEl.style.display = 'block';
                }
                if (loader) loader.style.display = 'none';
                _loading = false;
                return;
            }

            _page       = data.page;
            _totalPages = data.pages;

            renderRows(data.results, append);

            if (countEl) {
                const label = q ? `${data.total.toLocaleString('es-CO')} resultado${data.total !== 1 ? 's' : ''}`
                               : `${data.total.toLocaleString('es-CO')} contratos en total (SECOP I + II)`;
                countEl.textContent = label;
            }

            if (!data.results.length && !append) {
                if (emptyEl) emptyEl.style.display = 'block';
            }

            // Mostrar loader para siguiente página si hay más
            if (loader) {
                loader.style.display = (_page < _totalPages) ? 'block' : 'none';
            }

        } catch (err) {
            console.error('Error en búsqueda:', err);
            if (errorEl) {
                errorEl.textContent = '⚠ Error al conectar con el servidor. Recarga la página.';
                errorEl.style.display = 'block';
            }
            if (loader) loader.style.display = 'none';
        }

        _loading = false;
    };

    // ── Scroll infinito via IntersectionObserver ─────────────────────────────
    if (loader) {
        new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && _page < _totalPages && !_loading) {
                doSearch(_lastQuery, _page + 1, true);
            }
        }, { rootMargin: '300px' }).observe(loader);
    }

    // ── Input con debounce ───────────────────────────────────────────────────
    const triggerSearch = () => {
        const q = input.value.trim();
        _lastQuery = q;
        _page = 1;
        doSearch(q, 1, false);
    };

    input.addEventListener('input', () => {
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(triggerSearch, 350);
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { clearTimeout(_debounceTimer); triggerSearch(); }
    });

    if (btn) btn.addEventListener('click', () => { clearTimeout(_debounceTimer); triggerSearch(); });

    // ── Carga inicial: contratos recientes ───────────────────────────────────
    doSearch('', 1, false);
});
