// contexto.js — Filtros políticos + gobernantes + narrativas filtradas
document.addEventListener('DOMContentLoaded', () => {
    let _allNarrativas = [];
    let _modalChart    = null;

    const LABELS = {
        autocontratacion: { icon: '🔴', texto: 'Autocontratación' },
        nepotismo:        { icon: '🟠', texto: 'Ordenador Recurrente' },
        carrusel:         { icon: '🟡', texto: 'Carrusel de Contratos' },
        sobrecosto:       { icon: '⏱️', texto: 'Prórroga Excesiva' },
        empresa_reciente: { icon: '🟣', texto: 'Empresa Reciente Millonaria' },
    };

    const fmtFecha = (iso) => {
        if (!iso) return null;
        const [y, m, d] = iso.split('-');
        return `${d}/${m}/${y}`;
    };

    const buildMeta = (n) => {
        const chips = [];
        const raw = n.funcionario || n.ordenador || n.contratista || n.entidad || '';
        const nombre = escapeHtml(raw.length > 35 ? raw.slice(0, 35) + '…' : raw);
        if (nombre) chips.push(nombre);
        if (n.valor_m) chips.push(`$${(parseFloat(n.valor_m) / 1000).toFixed(1)}B COP`);
        if (n.valor_b) chips.push(`$${escapeHtml(String(n.valor_b))}B COP`);
        if (n.contratos) chips.push(`${parseInt(n.contratos, 10)} contratos`);
        if (n.entidades) chips.push(`${parseInt(n.entidades, 10)} entidades`);
        if (n.dias_prorroga) chips.push(`${parseInt(n.dias_prorroga, 10)} días prórroga`);
        const fi = fmtFecha(n.fecha_inicio), ff = fmtFecha(n.fecha_fin);
        let fechaChip = '';
        if (fi && ff)   fechaChip = `<span class="narrativa-chip fecha">📅 ${fi} → ${ff}</span>`;
        else if (fi)    fechaChip = `<span class="narrativa-chip fecha">📅 desde ${fi}</span>`;
        else if (ff)    fechaChip = `<span class="narrativa-chip fecha">📅 hasta ${ff}</span>`;
        return chips.map(c => `<span class="narrativa-chip">${c}</span>`).join('') + fechaChip;
    };

    const SECOP_URL = 'https://community.secop.gov.co';
    const buildVerificar = (n) => {
        if (n.tipo === 'autocontratacion')
            return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">${escapeHtml(n.contrato_id || '')}</a> en Colombia Compra Eficiente.`;
        return `<strong>Cómo verificarlo:</strong> Busca el NIT/CC <code>${escapeHtml(n.doc_id || '')}</code> en <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">SECOP II</a>.`;
    };

    const renderNarrativasMini = (data) => {
        const section = document.getElementById('ctx-narrativas-section');
        const grid    = document.getElementById('ctx-narrativas-grid');
        const count   = document.getElementById('ctx-narrativas-count');
        if (!grid) return;

        if (count) count.textContent = `${data.length} hallazgo${data.length !== 1 ? 's' : ''} en el periodo`;

        if (!data.length) {
            grid.innerHTML = '<p class="text-secondary js-notice">No se encontraron hallazgos para el periodo seleccionado.</p>';
            section?.classList.remove('hidden');
            return;
        }

        const shown = data.slice(0, 12);
        grid.innerHTML = shown.map(n => {
            const lbl    = LABELS[n.tipo] || { icon: '📋', texto: escapeHtml(n.tipo) };
            const nit    = escapeHtml(n.doc_id || '');
            const nombre = escapeHtml(n.contratista || n.funcionario || n.entidad || 'Caso detectado');
            return `
            <div class="narrativa-card tipo-${escapeHtml(n.tipo)}" data-nit="${nit}" data-nombre="${nombre}">
                <span class="narrativa-badge ${escapeHtml(n.tipo)}">${lbl.icon} ${lbl.texto}</span>
                <div class="narrativa-titulo">${escapeHtml(n.funcionario || n.contratista || n.entidad || 'Caso')}</div>
                <div class="narrativa-meta">${buildMeta(n)}</div>
                <p class="narrativa-texto">${escapeHtml(n.narrativa)}</p>
                <div class="narrativa-verificar">${buildVerificar(n)}</div>
            </div>`;
        }).join('');

        if (data.length > 12) {
            grid.insertAdjacentHTML('beforeend', `
            <p class="text-secondary js-section-notice">
                Mostrando 12 de ${data.length} resultados.
                <a href="/dashboard/hallazgos.html">Ver todos en Hallazgos →</a>
            </p>`);
        }
        section?.classList.remove('hidden');
    };

    // Modal de timeline
    const openTimelineModal = (nit, nombre) => {
        const modal = document.getElementById('timeline-modal');
        if (!modal) return;
        document.getElementById('timeline-modal-title').textContent = `${nombre} · NIT ${nit}`;
        if (_modalChart) { _modalChart.destroy(); _modalChart = null; }
        const oldCanvas = document.getElementById('timeline-modal-canvas');
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'timeline-modal-canvas';
        oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);
        const dd = document.getElementById('timeline-modal-detalle');
        if (dd) dd.innerHTML = '';
        modal.classList.remove('hidden');
        void modal.offsetHeight;
        document.body.style.overflow = 'hidden';
        _modalChart = renderTimelineGraph(newCanvas, nit);
    };

    const modal = document.getElementById('timeline-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.classList.contains('timeline-modal-backdrop') || e.target.closest('.timeline-modal-close')) {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
            }
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { modal?.classList.add('hidden'); document.body.style.overflow = ''; }
    });

    const setupFiltros = () => {
        const selP = document.getElementById('filtro-presidente');
        const selD = document.getElementById('filtro-departamento');
        const selC = document.getElementById('filtro-ciudad');
        const inI  = document.getElementById('filtro-fecha-inicio');
        const inF  = document.getElementById('filtro-fecha-fin');
        const btnA = document.getElementById('btn-aplicar-filtros');
        const btnL = document.getElementById('btn-limpiar-filtros');
        const panel = document.getElementById('panel-contextual');
        const grid  = document.getElementById('gobernantes-grid');

        if (!selP || typeof periodosPoliticos === 'undefined') return;

        periodosPoliticos.presidentes.forEach(p => {
            const o = document.createElement('option');
            o.value = p.id;
            o.textContent = `${p.nombre} (${p.inicio.split('-')[0]} - ${p.fin.split('-')[0]})`;
            selP.appendChild(o);
        });
        Object.keys(periodosPoliticos.gobernadores).sort().forEach(d => {
            const o = document.createElement('option'); o.value = d; o.textContent = d; selD.appendChild(o);
        });
        Object.keys(periodosPoliticos.alcaldes).sort().forEach(c => {
            const o = document.createElement('option'); o.value = c; o.textContent = c; selC.appendChild(o);
        });

        const checkSelects = () => {
            const has = inI.value || inF.value || selP.value;
            selD.disabled = !has; selC.disabled = !has;
            if (!has) { selD.value = ''; selC.value = ''; }
        };
        inI.addEventListener('change', checkSelects);
        inF.addEventListener('change', checkSelects);
        selP.addEventListener('change', (e) => {
            const p = periodosPoliticos.presidentes.find(x => x.id === e.target.value);
            if (p) { inI.value = p.inicio; inF.value = p.fin; }
            else   { inI.value = ''; inF.value = ''; }
            checkSelects();
        });

        btnL.addEventListener('click', () => {
            inI.value = ''; inF.value = ''; selP.value = ''; selD.value = ''; selC.value = '';
            checkSelects();
            panel.classList.add('hidden');
            document.getElementById('ctx-narrativas-section')?.classList.add('hidden');
        });

        btnA.addEventListener('click', () => {
            const fi = inI.value, ff = inF.value, dpto = selD.value, ciud = selC.value;
            if (fi || ff) {
                const checkDate = fi || ff;
                grid.innerHTML = '';
                const pres = politicosUtils.getPresidenteByDate(checkDate);
                if (pres) grid.innerHTML += `
                    <div class="gobernante-card"><div class="gobernante-icon">🇨🇴</div>
                    <div class="gobernante-info"><h4>Presidente</h4><h3>${pres.nombre}</h3>
                    <p>${pres.inicio.split('-')[0]} a ${pres.fin.split('-')[0]}</p></div></div>`;
                if (dpto) {
                    const g = politicosUtils.getGobernadorByDate(dpto, checkDate);
                    grid.innerHTML += `<div class="gobernante-card"><div class="gobernante-icon">🏛️</div>
                    <div class="gobernante-info"><h4>Gobernador / ${escapeHtml(dpto)}</h4>
                    <h3>${g ? escapeHtml(g.nombre) : 'No registrado'}</h3>
                    <p>${g ? g.inicio.split('-')[0] + ' a ' + g.fin.split('-')[0] : '—'}</p></div></div>`;
                }
                if (ciud) {
                    const a = politicosUtils.getAlcaldeByDate(ciud, checkDate);
                    grid.innerHTML += `<div class="gobernante-card"><div class="gobernante-icon">🏙️</div>
                    <div class="gobernante-info"><h4>Alcalde / ${escapeHtml(ciud)}</h4>
                    <h3>${a ? escapeHtml(a.nombre) : 'No registrado'}</h3>
                    <p>${a ? a.inicio.split('-')[0] + ' a ' + a.fin.split('-')[0] : '—'}</p></div></div>`;
                }
                if (grid.children.length) panel.classList.remove('hidden');
                else panel.classList.add('hidden');
            } else {
                panel.classList.add('hidden');
            }
            renderNarrativasMini(politicosUtils.filterByPeriodo(_allNarrativas, 'fecha', fi, ff));
        });
    };

    const init = async () => {
        try {
            const [narrativas, timelines] = await Promise.all([
                fetchDashboardJSON('narrativas.json'),
                fetchDashboardJSON('timelines.json').catch(() => null)
            ]);
            _allNarrativas = narrativas;
            if (timelines) window._timelines = timelines;
            setupFiltros();

            const ctxGrid = document.getElementById('ctx-narrativas-grid');
            if (ctxGrid) {
                ctxGrid.addEventListener('click', (e) => {
                    const card = e.target.closest('.narrativa-card');
                    if (!card || !card.dataset.nit) return;
                    openTimelineModal(card.dataset.nit, card.dataset.nombre || 'Contratista');
                });
            }
        } catch (e) {
            console.error('Error cargando contexto político:', e);
        }
    };

    init();
});
