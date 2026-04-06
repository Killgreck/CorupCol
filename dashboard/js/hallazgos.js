// hallazgos.js — Narrativas, filtros tipo, paginación, modal de timeline
document.addEventListener('DOMContentLoaded', () => {
    let _modalChart = null;

    const LABELS = {
        autocontratacion: { icon: '🔴', texto: 'Autocontratación' },
        nepotismo:        { icon: '🟠', texto: 'Ordenador Recurrente' },
        carrusel:         { icon: '🟡', texto: 'Carrusel de Contratos' },
        sobrecosto:       { icon: '⏱️', texto: 'Prórroga Excesiva' },
        empresa_reciente: { icon: '🟣', texto: 'Empresa Reciente Millonaria' },
    };
    const SECOP_URL = 'https://community.secop.gov.co';

    const buildVerificar = (n) => {
        if (n.tipo === 'autocontratacion')
            return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">${escapeHtml(n.contrato_id || '')}</a> en Colombia Compra Eficiente y compara "Ordenador del gasto" con "Representante legal".`;
        if (n.tipo === 'nepotismo')
            return `<strong>Cómo verificarlo:</strong> Busca la cédula <code>${escapeHtml(n.doc_ordenador || '')}</code> como ordenador en el buscador avanzado del SECOP II y filtra por contratista.`;
        if (n.tipo === 'carrusel')
            return `<strong>Cómo verificarlo:</strong> Busca el NIT <code>${escapeHtml(n.doc_id || '')}</code> en <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">SECOP II</a> y revisa las entidades que lo han contratado.`;
        return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">${escapeHtml(n.contrato_id || '')}</a> en Colombia Compra Eficiente y revisa las modificaciones.`;
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

    const renderNarrativas = (data) => {
        const grid = document.getElementById('narrativas-grid');
        if (!grid) return;
        let currentPage = 1;
        const ITEMS = 6;
        let currentData = data;

        const renderCards = (items, page = 1) => {
            const slice = items.slice((page - 1) * ITEMS, page * ITEMS);
            grid.innerHTML = slice.map(n => {
                const lbl   = LABELS[n.tipo] || { icon: '📋', texto: escapeHtml(n.tipo) };
                const nit   = escapeHtml(n.doc_id || '');
                const nombre = escapeHtml(n.contratista || n.funcionario || n.entidad || 'Caso detectado');
                return `
                <div class="narrativa-card tipo-${escapeHtml(n.tipo)}"
                     data-tipo="${escapeHtml(n.tipo)}" data-nit="${nit}" data-nombre="${nombre}">
                    <span class="narrativa-badge ${escapeHtml(n.tipo)}">${lbl.icon} ${lbl.texto}</span>
                    <div class="narrativa-titulo">${escapeHtml(n.funcionario || n.contratista || n.entidad || 'Caso detectado')}</div>
                    <div class="narrativa-meta">${buildMeta(n)}</div>
                    <p class="narrativa-texto">${escapeHtml(n.narrativa)}</p>
                    <div class="narrativa-verificar">${buildVerificar(n)}</div>
                    ${nit ? '<div class="narrativa-chart-hint">📊 Ver gráfica de contratos</div>' : ''}
                </div>`;
            }).join('');
            renderPagination(items.length, page);
        };

        const renderPagination = (total, page) => {
            const pages = Math.ceil(total / ITEMS);
            const pc = document.getElementById('narrativas-pagination');
            if (!pc) return;
            if (pages <= 1) { pc.classList.add('hidden'); return; }
            pc.classList.remove('hidden');
            let html = `<button class="page-btn" ${page === 1 ? 'disabled' : ''} data-page="${page - 1}">Anterior</button>`;
            for (let i = 1; i <= pages; i++) {
                if (i === 1 || i === pages || (i >= page - 1 && i <= page + 1))
                    html += `<button class="page-btn ${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
                else if (i === page - 2 || i === page + 2)
                    html += `<span class="page-dots">...</span>`;
            }
            html += `<button class="page-btn" ${page === pages ? 'disabled' : ''} data-page="${page + 1}">Siguiente</button>`;
            pc.innerHTML = html;
            pc.querySelectorAll('.page-btn:not(:disabled)').forEach(btn =>
                btn.addEventListener('click', (e) => {
                    currentPage = parseInt(e.target.dataset.page);
                    renderCards(currentData, currentPage);
                    document.getElementById('periodistas')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                })
            );
        };

        renderCards(currentData, currentPage);

        document.querySelectorAll('.filtro-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const tipo = btn.dataset.tipo;
                currentData = tipo === 'all' ? data : data.filter(n => n.tipo === tipo);
                currentPage = 1;
                renderCards(currentData, currentPage);
            });
        });
    };

    const openTimelineModal = (nit, nombre) => {
        const modal = document.getElementById('timeline-modal');
        document.getElementById('timeline-modal-title').textContent = `${nombre} · NIT ${nit}`;
        if (_modalChart) { _modalChart.destroy(); _modalChart = null; }
        const oldCanvas = document.getElementById('timeline-modal-canvas');
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'timeline-modal-canvas';
        oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);
        const detalleDiv = document.getElementById('timeline-modal-detalle');
        if (detalleDiv) detalleDiv.innerHTML = '';
        modal.classList.remove('hidden');
        void modal.offsetHeight;
        document.body.style.overflow = 'hidden';
        _modalChart = renderTimelineGraph(newCanvas, nit);
    };

    document.getElementById('timeline-modal').addEventListener('click', (e) => {
        if (e.target.classList.contains('timeline-modal-backdrop') || e.target.closest('.timeline-modal-close')) {
            document.getElementById('timeline-modal').classList.add('hidden');
            document.body.style.overflow = '';
        }
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.getElementById('timeline-modal').classList.add('hidden');
            document.body.style.overflow = '';
        }
    });

    const init = async () => {
        try {
            const [narrativas, timelines] = await Promise.all([
                fetchDashboardJSON('narrativas.json'),
                fetchDashboardJSON('timelines.json').catch(() => null)
            ]);
            if (timelines) window._timelines = timelines;

            renderNarrativas(narrativas);

            document.getElementById('narrativas-grid').addEventListener('click', (e) => {
                const card = e.target.closest('.narrativa-card');
                if (!card || !card.dataset.nit) return;
                openTimelineModal(card.dataset.nit, card.dataset.nombre || 'Contratista');
            });
        } catch (e) {
            console.error('Error cargando hallazgos:', e);
            const grid = document.getElementById('narrativas-grid');
            if (grid) grid.innerHTML = '<p class="text-secondary" style="padding:20px;text-align:center;">Error al cargar hallazgos. Verifica que los datos estén disponibles.</p>';
        }
    };

    init();
});
