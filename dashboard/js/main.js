document.addEventListener('DOMContentLoaded', () => {

    // ── Tasa de cambio USD/COP ───────────────────────────────────────────────────
    let _usdRate = 4200;     // fallback hasta que llegue la tasa real
    let _timelines = {};     // datos de timelines para gráficas inline
    let _budgetChart = null; // instancia Chart.js del donut presupuestal
    let _modalChart = null;  // instancia Chart.js del modal de timeline

    // _usdRatePromise garantiza que fetchUSDRate sólo hace UNA petición HTTP.
    // Cualquier llamada posterior recibe la misma Promise resuelta.
    let _usdRatePromise = null;

    const fetchUSDRate = () => {
        if (_usdRatePromise) return _usdRatePromise;
        _usdRatePromise = fetch('https://open.er-api.com/v6/latest/USD')
            .then(res => res.json())
            .then(data => {
                if (data.rates?.COP) _usdRate = data.rates.COP;
                return _usdRate;
            })
            .catch(() => _usdRate); // usa el fallback en error
        return _usdRatePromise;
    };

    // Formatea billones COP → USD con sufijo T/B/M inteligente
    const formatUSD = (billonesCOP) => {
        const usd = billonesCOP * 1e12 / _usdRate;
        if (usd >= 1e12) return `≈ USD ${(usd / 1e12).toFixed(2)} T`;
        if (usd >= 1e9) return `≈ USD ${(usd / 1e9).toFixed(1)} B`;
        if (usd >= 1e6) return `≈ USD ${(usd / 1e6).toFixed(1)} M`;
        return `≈ USD ${(usd / 1e3).toFixed(0)} K`;
    };

    // Inicia la carga de tasa en paralelo (no bloquea el dashboard)
    fetchUSDRate();

    // ── Helpers de UI para estados de carga y error ─────────────────────────────
    const showLoadingState = () => {
        ['counter-contratos', 'counter-valor', 'counter-anomalias'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '…';
        });
    };

    const showErrorState = (msg) => {
        const container = document.getElementById('stats');
        if (!container) return;
        const banner = document.createElement('div');
        banner.className = 'error-banner';
        banner.setAttribute('role', 'alert');
        banner.textContent = msg || 'Error al cargar los datos. Por favor recarga la página.';
        container.insertAdjacentElement('beforebegin', banner);
        ['counter-contratos', 'counter-valor', 'counter-anomalias'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '—';
        });
    };

    // 1. Cargar datos
    const loadData = async () => {
        showLoadingState();
        try {
            const [statsRes, carruselRes, nepotismoRes, sobrecostosRes, narrativasRes, timelinesRes] = await Promise.all([
                fetch('/static_dashboard/data/stats.json'),
                fetch('/static_dashboard/data/carrusel.json'),
                fetch('/static_dashboard/data/nepotismo.json'),
                fetch('/static_dashboard/data/sobrecostos.json'),
                fetch('/static_dashboard/data/narrativas.json'),
                fetch('/static_dashboard/data/timelines.json').catch(() => null)
            ]);

            const stats = await statsRes.json();
            const carrusel = await carruselRes.json();
            const nepotismo = await nepotismoRes.json();
            const sobrecostos = await sobrecostosRes.json();
            const narrativas = await narrativasRes.json();

            // Cargar timelines de forma segura para no romper la app si falla
            _timelines = {};
            try {
                if (timelinesRes && timelinesRes.ok) {
                    _timelines = await timelinesRes.json();
                }
            } catch (err) {
                console.warn("No se pudo cargar timelines.json", err);
            }

            // Llenar interfaz
            updateStats(stats);
            renderNarrativas(narrativas);

            // Click en narrativa-card → abrir modal de gráfica (se registra una sola vez)
            document.getElementById('narrativas-grid').addEventListener('click', (e) => {
                const card = e.target.closest('.narrativa-card');
                if (!card || !card.dataset.nit) return;
                openTimelineModal(card.dataset.nit, card.dataset.nombre || 'Contratista');
            });

            renderTable('table-carrusel', carrusel, ['display_name', 'c.doc_id', 'entidades_distintas', 'total_contratos', 'total_valor_b'], true);
            renderTable('table-nepotismo', nepotismo, ['p.nombre_display', 'p.doc_id', '_nombre_contratista_display', 'contratos_juntos', 'valor_total_b'], true);
            renderSobrecostosTable(sobrecostos);

            // 8. Configurar filtros políticos
            setupFiltrosPoliticos(narrativas);

            // Configurar buscador global
            setupSearch([...carrusel.map(i => ({ ...i, _type: 'Carrusel' })),
            ...nepotismo.map(i => ({ ...i, _type: 'Nepotismo' })),
            ...sobrecostos.map(i => ({ ...i, _type: 'Sobrecosto' }))]);

        } catch (error) {
            console.error("Error cargando datos:", error);
            showErrorState('Error al cargar los datos. Verifica que los archivos JSON estén disponibles y recarga la página.');
        }
    };

    // 2. Actualizar contadores animados
    const updateStats = async (stats) => {
        animateValue('counter-contratos', 0, stats.total_contratos, 2000, true);
        animateValue('counter-valor', 0, stats.valor_total_b, 2000, false, '$', 'B');
        animateValue('counter-anomalias', 0,
            stats.casos_carrusel + stats.casos_nepotismo +
            stats.casos_sobrecosto + (stats.casos_autocontratacion || 0), 2000, true);

        document.getElementById('finding-carrusel').textContent = stats.casos_carrusel;
        document.getElementById('finding-nepotismo').textContent = stats.casos_nepotismo;
        document.getElementById('finding-sobrecostos').textContent = stats.casos_sobrecosto;
        if (document.getElementById('footer-date'))
            document.getElementById('footer-date').textContent = stats.fecha.split('T')[0];

        // Mostrar USD tras obtener la tasa real (reutiliza la Promise ya iniciada, sin doble fetch)
        const rate = await fetchUSDRate();
        const usdEl = document.getElementById('counter-valor-usd');
        if (usdEl) {
            const usd = stats.valor_total_b * 1e12 / rate;
            const usdT = (usd / 1e12).toFixed(2);
            usdEl.textContent = `≈ USD ${usdT} T`;
            usdEl.title = `Tasa en tiempo real: 1 USD = ${rate.toFixed(0)} COP`;
        }

        if (stats.presupuesto_origen_nota) {
            const sourceEl = document.getElementById('budget-source');
            if (sourceEl) sourceEl.textContent = `📝 Origen: ${stats.presupuesto_origen_nota}`;
        }
        
        // Renderizar gráfica de anillo de presupuesto
        renderBudgetChart(stats);
    };

    const renderBudgetChart = (stats) => {
        const wrapper = document.getElementById('budget-chart-wrapper');
        const canvas = document.getElementById('budget-donut-chart');
        if (!wrapper || !canvas) return;

        // Mostrar el wrapper quitando la clase hidden y forzar reflow síncrono
        // ANTES de que Chart.js mida las dimensiones del contenedor.
        // display:none !important (de .hidden) hace que offsetHeight=0;
        // leer wrapper.offsetHeight fuerza al browser a recalcular el layout.
        wrapper.classList.remove('hidden');
        void wrapper.offsetHeight; // fuerza reflow síncrono

        const ctx = canvas.getContext('2d');
        if (_budgetChart) {
            _budgetChart.destroy();
        }

        const total = parseFloat(stats.valor_total_b) || 0;
        const carrusel = parseFloat(stats.total_val_carrusel_b) || 0;
        const nepotismo = parseFloat(stats.total_val_nepotismo_b) || 0;
        const sobrecostos = parseFloat(stats.total_val_sobrecostos_b) || 0;

        const anomaliasTotal = carrusel + nepotismo + sobrecostos;
        const resto = Math.max(0, total - anomaliasTotal);

        _budgetChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [
                    'Contratación Estándar (Resto PGN)',
                    'Carrusel de Contratos',
                    'Asignación Repetitiva (Nepotismo)',
                    'Sobrecostos de Prórroga'
                ],
                datasets: [{
                    data: [resto, carrusel, nepotismo, sobrecostos],
                    backgroundColor: [
                        '#2ea043', // Verde para OK
                        '#d29922', // Amarillo
                        '#f0883e', // Naranja
                        '#da3633'  // Rojo
                    ],
                    borderColor: '#0d1117',
                    borderWidth: 2,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                color: '#c9d1d9',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#8b949e', padding: 20, font: { family: 'Inter', size: 12 } }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 34, 0.95)',
                        titleColor: '#c9d1d9',
                        bodyColor: '#e6edf3',
                        borderColor: '#30363d',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed !== null) {
                                    const valueB = context.parsed;
                                    const percentage = total > 0 ? ((valueB / total) * 100).toFixed(1) : 0;
                                    label += `$${valueB.toLocaleString('es-CO', { minimumFractionDigits: 1 })}B COP (${percentage}%)`;
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    };

    const animateValue = (id, start, end, duration, noDecimals = false, prefix = '', suffix = '') => {
        const obj = document.getElementById(id);
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // ease out cubic: aplica la curva tanto al avance como a la interpolación
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = (easeOut * (end - start) + start);

            if (noDecimals) {
                obj.textContent = prefix + Math.floor(current).toLocaleString('es-CO') + suffix;
            } else {
                obj.textContent = prefix + current.toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + suffix;
            }
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };

    // 3. Renderizar Tablas Genéricas (Carrusel, Nepotismo)
    const renderTable = (tableId, data, columns, addValueBar = false) => {
        const tbody = document.querySelector(`#${tableId} tbody`);
        if (!tbody) return;
        tbody.innerHTML = '';

        // Encontrar el valor máximo para la barra proporcional
        const maxVal = addValueBar ? Math.max(...data.map(d => parseFloat(d[columns[columns.length - 1]]) || 0)) : 0;

        data.forEach(row => {
            const tr = document.createElement('tr');
            columns.forEach((col, idx) => {
                const td = document.createElement('td');
                let val = row[col];

                // Formateo de dinero (asumiendo que la última columna es dinero_b si addValueBar es true)
                if (addValueBar && idx === columns.length - 1) {
                    const numVal = parseFloat(val) || 0;
                    td.innerHTML = `<strong>$${numVal.toLocaleString('es-CO', { minimumFractionDigits: 1 })}B COP</strong>
                        <div class="valor-usd">${formatUSD(numVal)}</div>`;

                    const pct = maxVal > 0 ? (numVal / maxVal) * 100 : 0;
                    const barContainer = document.createElement('div');
                    barContainer.className = 'value-bar-container';
                    barContainer.innerHTML = `<div class="value-bar" style="width: ${pct}%"></div>`;
                    td.appendChild(barContainer);
                } else {
                    td.textContent = val !== undefined && val !== null ? val : 'N/A';
                    if (col.includes('doc_id') || col === 'ct.id') {
                        td.className = 'mono';
                    }
                }
                tr.appendChild(td);
            });
            // Expansión para gráficas
            const isCarrusel = tableId === 'table-carrusel' && row['c.doc_id'];
            const isNepotismo = tableId === 'table-nepotismo' && row['p.doc_id'];

            if (isCarrusel || isNepotismo) {
                tr.addEventListener('click', () => {
                    const doc_id = isCarrusel ? row['c.doc_id'] : row['p.doc_id'];
                    const display_text = isCarrusel ? row.display_name : row['p.nombre_display'] || row['p.nombre'];
                    const existingChartRow = tr.nextElementSibling;

                    if (existingChartRow && existingChartRow.classList.contains('chart-row')) {
                        // Toggle logic
                        const wrapper = existingChartRow.querySelector('.chart-container-wrapper');
                        if (wrapper.classList.contains('expanded')) {
                            wrapper.classList.remove('expanded');
                            setTimeout(() => existingChartRow.remove(), 300);
                        }
                    } else {
                        // Close any other open charts
                        document.querySelectorAll('.chart-row').forEach(cr => cr.remove());

                        // Create chart row
                        const chartTr = document.createElement('tr');
                        chartTr.className = 'chart-row';
                        const chartTd = document.createElement('td');
                        chartTd.colSpan = columns.length;

                        const wrapper = document.createElement('div');
                        wrapper.className = 'chart-container-wrapper';

                        const container = document.createElement('div');
                        container.className = 'chart-container';

                        const title = document.createElement('div');
                        title.className = 'chart-title';
                        title.textContent = isCarrusel ? 
                            `Línea de Tiempo de Contratación: ${display_text} (NIT: ${doc_id})` :
                            `Línea de Tiempo como Ordenador del Gasto: ${display_text} (CC: ${doc_id})`;

                        const canvas = document.createElement('canvas');
                        container.appendChild(title);
                        container.appendChild(canvas);
                        wrapper.appendChild(container);
                        chartTd.appendChild(wrapper);
                        chartTr.appendChild(chartTd);

                        tr.after(chartTr);

                        // Añadir .expanded en el siguiente frame (dispara la transición CSS).
                        // Chart.js se crea DESPUÉS de que la transición (300ms) termine,
                        // así max-height ya alcanzó 350px y el canvas tiene dimensiones reales.
                        requestAnimationFrame(() => {
                            wrapper.classList.add('expanded');
                        });
                        setTimeout(() => renderTimelineGraph(canvas, doc_id), 320);
                    }
                });
            }

            tbody.appendChild(tr);
        });

        setupTableSorting(tableId, data, columns, addValueBar);
    };

    // Renderizar gráfico con Chart.js
    // Cache de datos de detalle de contratos por NIT (cargados bajo demanda)
    const _contratoCache = {};

    const fetchDetalleContratos = async (nit) => {
        if (_contratoCache[nit] !== undefined) return _contratoCache[nit];
        try {
            const res = await fetch(`/static_dashboard/data/contratos/${escapeHtml(nit)}.json`);
            if (!res.ok) throw new Error('not found');
            _contratoCache[nit] = await res.json();
        } catch (_) {
            _contratoCache[nit] = null;
        }
        return _contratoCache[nit];
    };

    // Muestra tabla de detalle de contratos para un período dado
    const mostrarTablaDetalle = (container, periodoData, periodo, nit) => {
        // Limpiar tabla anterior
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
            <th>ID Contrato</th>
            <th>Objeto</th>
            <th>Entidad</th>
            <th>Contratista</th>
            <th>Valor (COP)</th>
            <th>Fecha Firma</th>
            <th>Fecha Inicio</th>
            <th>Fecha Fin</th>
            <th>Estado</th>
            <th>Modalidad</th>
            <th>Días Adicionados</th>
            <th>Enlace</th>
        </tr></thead>`;

        const tbody = document.createElement('tbody');
        periodoData.forEach(c => {
            const tr = document.createElement('tr');
            const valor = c.valor_del_contrato
                ? `$${parseFloat(c.valor_del_contrato).toLocaleString('es-CO', {minimumFractionDigits: 0})}`
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

    const renderTimelineGraph = (canvas, nit) => {
        const data = _timelines[nit];

        if (!data || data.length === 0) {
            const w = canvas.clientWidth || canvas.offsetWidth || 300;
            const h = canvas.clientHeight || canvas.offsetHeight || 150;
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.font = '14px Inter';
            ctx.fillStyle = '#8b949e';
            ctx.textAlign = 'center';
            ctx.fillText('No hay datos históricos disponibles', w / 2, h / 2);
            return;
        }

        const labels = data.map(d => d.fecha);
        const values = data.map(d => d.valor_total_b || 0);

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
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
                cursor: 'pointer',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const idx = context.dataIndex;
                                const numC = data[idx] ? data[idx].num_contratos : 0;
                                const val = context.parsed.y;
                                return [
                                    `Valor: $${val.toLocaleString('es-CO', {minimumFractionDigits: 3})}B COP`,
                                    `Contratos: ${numC} · Click para ver detalle`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#8b949e' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#e6edf3' }
                    }
                },
                onClick: async (event, elements) => {
                    if (!elements.length) return;
                    const idx = elements[0].index;
                    const periodo = labels[idx];
                    // Para el modal usa su div dedicado; para inline usa el chart-container
                    const modalDetalle = document.getElementById('timeline-modal-detalle');
                    const container = modalDetalle && canvas.closest('.timeline-modal-body')
                        ? modalDetalle
                        : (canvas.closest('.chart-container') || canvas.parentElement);
                    const detalles = await fetchDetalleContratos(nit);
                    const periodoData = detalles ? (detalles[periodo] || []) : [];
                    mostrarTablaDetalle(container, periodoData, periodo, nit);
                }
            }
        });

        // Cursor pointer al pasar sobre barras
        canvas.style.cursor = 'pointer';
        return chart;
    };

    // Modal: abre la gráfica de contratos en el tiempo para un NIT
    const openTimelineModal = (nit, nombre) => {
        const modal = document.getElementById('timeline-modal');
        document.getElementById('timeline-modal-title').textContent = `${nombre} · NIT ${nit}`;

        if (_modalChart) {
            _modalChart.destroy();
            _modalChart = null;
        }

        // Reemplazar canvas para evitar el error "Canvas is already in use"
        const oldCanvas = document.getElementById('timeline-modal-canvas');
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'timeline-modal-canvas';
        oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);

        // Limpiar tabla de detalle anterior
        const detalleDiv = document.getElementById('timeline-modal-detalle');
        if (detalleDiv) detalleDiv.innerHTML = '';

        modal.classList.remove('hidden');
        void modal.offsetHeight; // fuerza reflow síncrono antes de que Chart.js mida
        document.body.style.overflow = 'hidden';

        _modalChart = renderTimelineGraph(newCanvas, nit);
    };

    // Cerrar modal al pulsar backdrop, botón X o Escape
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

    // Escapa caracteres HTML para prevenir XSS en strings de datos externos
    const escapeHtml = (str) => {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    // 3b. Renderizar narrativas para periodistas
    const renderNarrativas = (data) => {
        const grid = document.getElementById('narrativas-grid');
        if (!grid) return;

        const LABELS = {
            autocontratacion: { icon: '🔴', texto: 'Autocontratación' },
            nepotismo: { icon: '🟠', texto: 'Ordenador Recurrente' },
            carrusel: { icon: '🟡', texto: 'Carrusel de Contratos' },
            sobrecosto: { icon: '⏱️', texto: 'Prórroga Excesiva' },
            empresa_reciente: { icon: '🟣', texto: 'Empresa Reciente Millonaria' },
        };

        const SECOP_URL = 'https://community.secop.gov.co';

        const buildVerificar = (n) => {
            const tipo = n.tipo;
            if (tipo === 'autocontratacion') {
                return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">${escapeHtml(n.contrato_id || '')}</a> en Colombia Compra Eficiente y compara "Ordenador del gasto" con "Representante legal".`;
            } else if (tipo === 'nepotismo') {
                return `<strong>Cómo verificarlo:</strong> Busca la cédula <code>${escapeHtml(n.doc_ordenador || '')}</code> como ordenador en el buscador avanzado del SECOP II y filtra por contratista.`;
            } else if (tipo === 'carrusel') {
                return `<strong>Cómo verificarlo:</strong> Busca el NIT <code>${escapeHtml(n.doc_id || '')}</code> en <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">SECOP II</a> y revisa las entidades que lo han contratado.`;
            } else {
                return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank" rel="noopener noreferrer">${escapeHtml(n.contrato_id || '')}</a> en Colombia Compra Eficiente y revisa las modificaciones.`;
            }
        };

        const fmtFecha = (iso) => {
            if (!iso) return null;
            const [y, m, d] = iso.split('-');
            return `${d}/${m}/${y}`;
        };

        const buildMeta = (n) => {
            const chips = [];
            const nombreRaw = n.funcionario || n.ordenador || n.contratista || n.entidad || '';
            const nombre = escapeHtml(nombreRaw.length > 35 ? nombreRaw.slice(0, 35) + '…' : nombreRaw);
            if (nombre) chips.push(nombre);
            if (n.valor_m) chips.push(`$${(parseFloat(n.valor_m) / 1000).toFixed(1)}B COP`);
            if (n.valor_b) chips.push(`$${escapeHtml(String(n.valor_b))}B COP`);
            if (n.contratos) chips.push(`${parseInt(n.contratos, 10)} contratos`);
            if (n.entidades) chips.push(`${parseInt(n.entidades, 10)} entidades`);
            if (n.dias_prorroga) chips.push(`${parseInt(n.dias_prorroga, 10)} días prórroga`);

            const fi = fmtFecha(n.fecha_inicio);
            const ff = fmtFecha(n.fecha_fin);
            let fechaChip = '';
            if (fi && ff) {
                fechaChip = `<span class="narrativa-chip fecha">📅 ${fi} → ${ff}</span>`;
            } else if (fi) {
                fechaChip = `<span class="narrativa-chip fecha">📅 desde ${fi}</span>`;
            } else if (ff) {
                fechaChip = `<span class="narrativa-chip fecha">📅 hasta ${ff}</span>`;
            }

            return chips.map(c => `<span class="narrativa-chip">${c}</span>`).join('') + fechaChip;
        };

        let currentPage = 1;
        const itemsPerPage = 6; // Cantidad de "cuadraditos" por página
        let currentData = data;

        const renderCards = (items, page = 1) => {
            const start = (page - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const paginatedItems = items.slice(start, end);

            grid.innerHTML = paginatedItems.map(n => {
                const lbl = LABELS[n.tipo] || { icon: '📋', texto: escapeHtml(n.tipo) };
                const nit = escapeHtml(n.doc_id || '');
                const nombre = escapeHtml(n.contratista || n.funcionario || n.entidad || 'Caso detectado');
                // narrativa y verificar pueden contener HTML controlado (buildVerificar genera links propios)
                // pero los campos de texto del dataset se escapan antes de insertarse
                const tituloDisplay = escapeHtml(n.funcionario || n.contratista || n.entidad || 'Caso detectado');
                const narrativaEscapada = escapeHtml(n.narrativa);
                return `
                <div class="narrativa-card tipo-${escapeHtml(n.tipo)}" data-tipo="${escapeHtml(n.tipo)}" data-nit="${nit}" data-nombre="${nombre}">
                    <span class="narrativa-badge ${escapeHtml(n.tipo)}">${lbl.icon} ${lbl.texto}</span>
                    <div class="narrativa-titulo">${tituloDisplay}</div>
                    <div class="narrativa-meta">${buildMeta(n)}</div>
                    <p class="narrativa-texto">${narrativaEscapada}</p>
                    <div class="narrativa-verificar">${buildVerificar(n)}</div>
                    ${nit ? '<div class="narrativa-chart-hint">📊 Ver gráfica de contratos</div>' : ''}
                </div>`;
            }).join('');

            renderPagination(items.length, page);
        };

        const renderPagination = (totalItems, page) => {
            const totalPages = Math.ceil(totalItems / itemsPerPage);
            const paginationContainer = document.getElementById('narrativas-pagination');
            if (!paginationContainer) return;

            if (totalPages <= 1) {
                paginationContainer.classList.add('hidden');
                return;
            }
            paginationContainer.classList.remove('hidden');

            let html = '';

            // Botón Anterior
            html += `<button class="page-btn" ${page === 1 ? 'disabled' : ''} data-page="${page - 1}">Anterior</button>`;

            // Números de página con elipsis
            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
                    html += `<button class="page-btn ${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
                } else if (i === page - 2 || i === page + 2) {
                    html += `<span class="page-dots">...</span>`;
                }
            }

            // Botón Siguiente
            html += `<button class="page-btn" ${page === totalPages ? 'disabled' : ''} data-page="${page + 1}">Siguiente</button>`;

            paginationContainer.innerHTML = html;

            // Asignar eventos de click a la paginación
            paginationContainer.querySelectorAll('.page-btn:not(:disabled)').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const newPage = parseInt(e.target.dataset.page);
                    currentPage = newPage;
                    renderCards(currentData, currentPage);
                    // Hacer scroll suave hacia el título de la sección para una mejor UX
                    document.getElementById('periodistas').scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
            });
        };

        renderCards(currentData, currentPage);

        // Filtros
        document.querySelectorAll('.filtro-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const tipo = btn.dataset.tipo;
                currentData = tipo === 'all' ? data : data.filter(n => n.tipo === tipo);
                currentPage = 1; // Volver a la primera página al cambiar de filtro
                renderCards(currentData, currentPage);
            });
        });
    };

    // 4. Renderizar Tabla Sobrecostos (Especial por badges)
    const renderSobrecostosTable = (data) => {
        const tbody = document.querySelector('#table-sobrecostos tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        // Actualizar data-sort en los headers para que coincidan con los campos reales del JSON
        const sortMap = {
            'entidad': 'entidad_nombre',
            'contratista': 'contratista_nombre',
            'contrato_id': 'ct.id',
            'dias_prorroga': 'ct.dias_adicionados',
            'valor_m': 'ct.valor'
        };
        document.querySelectorAll('#table-sobrecostos th[data-sort]').forEach(th => {
            const oldKey = th.getAttribute('data-sort');
            if (sortMap[oldKey]) th.setAttribute('data-sort', sortMap[oldKey]);
        });

        data.forEach(row => {
            const tr = document.createElement('tr');

            // Entidad — el JSON puede traer placeholder 'Entidad (NIT: N/A)' si Neo4j no tiene el nombre
            let td = document.createElement('td');
            const entidadNombre = row.entidad_nombre || row.entidad || '';
            td.textContent = (entidadNombre && !entidadNombre.startsWith('Entidad (NIT'))
                ? entidadNombre
                : (row.display_name && row.display_name !== 'Desconocido' ? row.display_name : 'Sin nombre');
            tr.appendChild(td);

            // Contratista
            td = document.createElement('td');
            const contratistaNombre = row.contratista_nombre || row.contratista || '';
            td.textContent = (contratistaNombre && !contratistaNombre.startsWith('Contratista (DOC'))
                ? contratistaNombre
                : (row.display_name && row.display_name !== 'Desconocido' ? row.display_name : 'Sin nombre');
            tr.appendChild(td);

            // ID Contrato
            td = document.createElement('td');
            td.className = 'mono';
            td.textContent = row['ct.id'] || row.contrato_id || 'N/A';
            tr.appendChild(td);

            // Días extra con badge
            td = document.createElement('td');
            const dias = parseInt(row['ct.dias_adicionados'] || row.dias_prorroga) || 0;
            let badgeClass = 'badge-orange';
            if (dias > 365) badgeClass = 'badge-red';
            td.innerHTML = `<span class="badge ${badgeClass}">${dias.toLocaleString('es-CO')} días</span>`;
            tr.appendChild(td);

            // Valor en COP — el JSON trae ct.valor en pesos, convertimos a billones para consistencia
            td = document.createElement('td');
            const valorCOP = parseFloat(row['ct.valor']) || 0;
            const valorB = valorCOP / 1e12;
            const valorM = valorCOP / 1e6;
            // Si el valor es >= 1 billón mostramos en B, si no en M
            if (valorB >= 0.001) {
                td.innerHTML = `<strong>$${valorB.toLocaleString('es-CO', { minimumFractionDigits: 3 })}B COP</strong>
                    <div class="valor-usd">${formatUSD(valorB)}</div>`;
            } else {
                td.innerHTML = `<strong>$${Math.round(valorM).toLocaleString('es-CO')} M COP</strong>
                    <div class="valor-usd">${formatUSD(valorB)}</div>`;
            }
            tr.appendChild(td);

            // Objeto (truncado con tooltip nativo)
            td = document.createElement('td');
            const objTxt = row['ct.objeto'] || row.objeto || 'Sin descripción';
            if (objTxt.length > 60) {
                td.textContent = objTxt.substring(0, 60) + '…';
                td.title = objTxt;
            } else {
                td.textContent = objTxt;
            }
            tr.appendChild(td);

            tbody.appendChild(tr);
        });

        setupTableSorting('table-sobrecostos', data, ['entidad_nombre', 'contratista_nombre', 'ct.id', 'ct.dias_adicionados', 'ct.valor'], false, renderSobrecostosTable);
    };

    // 5. Ordenamiento de Tablas
    const setupTableSorting = (tableId, data, columns, addValueBar, customRender = null) => {
        const headers = document.querySelectorAll(`#${tableId} th[data-sort]`);
        headers.forEach(th => {
            // Remover listeners previos clonando
            const newTh = th.cloneNode(true);
            th.parentNode.replaceChild(newTh, th);

            newTh.addEventListener('click', () => {
                const sortKey = newTh.getAttribute('data-sort');
                const isDesc = newTh.classList.contains('sorted-desc');

                // Reset all headers
                document.querySelectorAll(`#${tableId} th`).forEach(h => {
                    h.classList.remove('sorted-asc', 'sorted-desc');
                    const icon = h.querySelector('.sort-icon');
                    if (icon) icon.textContent = '↕';
                });

                // Set current header
                newTh.classList.add(isDesc ? 'sorted-asc' : 'sorted-desc');
                const icon = newTh.querySelector('.sort-icon');
                if (icon) icon.textContent = isDesc ? '↑' : '↓';

                // Sort data
                data.sort((a, b) => {
                    let valA = a[sortKey];
                    let valB = b[sortKey];

                    // Si es número, parsear
                    if (typeof valA === 'number' || (typeof valA === 'string' && !isNaN(parseFloat(valA)) && isFinite(valA))) {
                        valA = parseFloat(valA) || 0;
                        valB = parseFloat(valB) || 0;
                        return isDesc ? valA - valB : valB - valA;
                    }

                    // Strings
                    valA = String(valA || '').toLowerCase();
                    valB = String(valB || '').toLowerCase();
                    if (valA < valB) return isDesc ? -1 : 1;
                    if (valA > valB) return isDesc ? 1 : -1;
                    return 0;
                });

                // Render again
                if (customRender) {
                    customRender(data);
                } else {
                    renderTable(tableId, data, columns, addValueBar);
                }
            });
        });
    };

    // 6. Buscador Global
    const setupSearch = (allData) => {
        const input = document.getElementById('global-search');
        const searchBtn = document.querySelector('.search-btn');
        const resultsContainer = document.getElementById('search-results');

        const performSearch = () => {
            const query = input.value.toLowerCase().trim();
            if (query.length < 3) {
                resultsContainer.classList.add('hidden');
                return;
            }

            const results = allData.filter(item => {
                // Buscar en todos los valores del objeto
                return Object.values(item).some(val =>
                    String(val).toLowerCase().includes(query)
                );
            }).slice(0, 15); // max 15

            resultsContainer.innerHTML = '';

            if (results.length === 0) {
                resultsContainer.innerHTML = '<div class="search-item"><div class="search-item-title text-secondary">No se encontraron resultados para "' + escapeHtml(query) + '"</div></div>';
            } else {
                results.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'search-item';

                    let title = '';
                    let desc = '';
                    let badgeClass = '';

                    if (item._type === 'Carrusel') {
                        title = escapeHtml(item.display_name || 'Desconocido');
                        desc = escapeHtml(`NIT: ${item['c.doc_id'] || 'N/A'} - ${item.entidades_distintas} Entidades - ${item.total_contratos} Contratos`);
                        badgeClass = 'badge-carrusel';
                    } else if (item._type === 'Nepotismo') {
                        title = escapeHtml(`${item.p?.nombre_display || item['p.nombre'] || ''} ↔ ${item._nombre_contratista_display || item.display_name || ''}`);
                        desc = escapeHtml(`CC: ${item['p.doc_id'] || 'N/A'} - Contratos juntos: ${item.contratos_juntos}`);
                        badgeClass = 'badge-nepotismo';
                    } else if (item._type === 'Sobrecosto') {
                        const cNombre = item['ct.contratista'] || item.contratista_nombre || item.contratista || '';
                        title = escapeHtml(cNombre && !cNombre.startsWith('Contratista (DOC') ? cNombre : (item['ct.id'] || 'Desconocido'));
                        const eNombre = item['ct.entidad'] || item.entidad_nombre || item.entidad || '';
                        desc = escapeHtml(`ID: ${item['ct.id'] || item.contrato_id || 'N/A'} — ${item['ct.dias_adicionados'] || item.dias_prorroga || 0} días extra — Entidad: ${eNombre && !eNombre.startsWith('Entidad (NIT') ? eNombre : 'Sin nombre'}`);
                        badgeClass = 'badge-sobrecosto';
                    }

                    div.innerHTML = `
                        <div>
                            <div class="search-item-title">${title} <span class="badge ${badgeClass}">${escapeHtml(item._type)}</span></div>
                            <div class="search-item-desc mono">${desc}</div>
                        </div>
                    `;
                    resultsContainer.appendChild(div);
                });
            }
            resultsContainer.classList.remove('hidden');
        };

        input.addEventListener('input', performSearch);
        searchBtn.addEventListener('click', performSearch);

        // Hide config click outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-section')) {
                resultsContainer.classList.add('hidden');
            }
        });
    };

    // 7. Descarga CSV ZIP
    const setupDownloadBtn = () => {
        const btn = document.getElementById('btn-download');
        if (!btn) return;

        btn.addEventListener('click', async () => {
            btn.innerHTML = '<span class="btn-icon">⏳</span> Generando ZIP...';
            btn.disabled = true;

            try {
                // Fetch directly from our generated reports/csv
                // In a true static site, we'd fetch them from where they are hosted.
                // Assuming we copy them to data/ o we fetch via relative path
                // For this project structure we fetch from ../reports/csv/ which works in local dev
                // If it's github pages we might need to put them inside the dashboard dir. 
                // Let's assume the build script moved them or we fetch them relative.
                // It's safer to fetch the JSONs we already have and convert them to CSV string here using JSZip
                const [carruselRes, nepotismoRes, sobrecostosRes] = await Promise.all([
                    fetch('/static_dashboard/data/carrusel.json'),
                    fetch('/static_dashboard/data/nepotismo.json'),
                    fetch('/static_dashboard/data/sobrecostos.json')
                ]);

                const c_data = await carruselRes.json();
                const n_data = await nepotismoRes.json();
                const s_data = await sobrecostosRes.json();

                const toCSV = (data, keys) => {
                    const header = keys.join(',') + '\n';
                    const rows = data.map(obj => keys.map(k => {
                        let cell = obj[k] === null || obj[k] === undefined ? '' : String(obj[k]);
                        cell = cell.replace(/"/g, '""');
                        if (cell.search(/("|,|\n)/g) >= 0) cell = `"${cell}"`;
                        return cell;
                    }).join(',')).join('\n');
                    return header + rows;
                };

                const zip = new JSZip();
                zip.file("carruseles_top50.csv", toCSV(c_data, ['display_name', 'c.doc_id', 'entidades_distintas', 'total_contratos', 'total_valor', 'total_valor_b']));
                zip.file("nepotismo_top50.csv", toCSV(n_data, ['p.nombre', 'p.doc_id', 'display_name', 'c.doc_id', 'contratos_juntos', 'valor_total', 'valor_total_b']));
                zip.file("sobrecostos_top50.csv", toCSV(s_data, ['entidad', 'contratista', 'contrato_id', 'dias_prorroga', 'valor_m', 'objeto', 'alerta']));

                const content = await zip.generateAsync({ type: "blob" });

                // Trigger download
                const link = document.createElement('a');
                link.href = URL.createObjectURL(content);
                link.download = `CorupCol_Datos_Export_${new Date().toISOString().split('T')[0]}.zip`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                btn.innerHTML = '<span class="btn-icon">✅</span> ¡Descargado!';
                setTimeout(() => {
                    btn.innerHTML = '<span class="btn-icon">📦</span> Descargar Todos los Datos (ZIP)';
                    btn.disabled = false;
                }, 3000);
            } catch (error) {
                console.error("Error generando ZIP:", error);
                btn.innerHTML = '<span class="btn-icon">❌</span> Error. Intenta de nuevo.';
                btn.disabled = false;
            }
        });
    };

    // 8. Filtros Políticos Contextuales
    const setupFiltrosPoliticos = (allNarrativas) => {
        const selPresidente = document.getElementById('filtro-presidente');
        const selDepto = document.getElementById('filtro-departamento');
        const selCiudad = document.getElementById('filtro-ciudad');
        const inInicio = document.getElementById('filtro-fecha-inicio');
        const inFin = document.getElementById('filtro-fecha-fin');
        const btnAplicar = document.getElementById('btn-aplicar-filtros');
        const btnLimpiar = document.getElementById('btn-limpiar-filtros');
        const panelContextual = document.getElementById('panel-contextual');
        const gobernantesGrid = document.getElementById('gobernantes-grid');

        if (!selPresidente || typeof periodosPoliticos === 'undefined') return;

        // Llenar presidencias
        periodosPoliticos.presidentes.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.nombre} (${p.inicio.split('-')[0]} - ${p.fin.split('-')[0]})`;
            selPresidente.appendChild(opt);
        });

        // Llenar gobernaciones
        Object.keys(periodosPoliticos.gobernadores).sort().forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            selDepto.appendChild(opt);
        });

        // Llenar alcaldías
        Object.keys(periodosPoliticos.alcaldes).sort().forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            selCiudad.appendChild(opt);
        });

        // Habilitar selects condicionalmente
        const checkSelects = () => {
            const hasDate = inInicio.value || inFin.value || selPresidente.value;
            selDepto.disabled = !hasDate;
            selCiudad.disabled = !hasDate;
            if (!hasDate) {
                selDepto.value = "";
                selCiudad.value = "";
            }
        };

        inInicio.addEventListener('change', checkSelects);
        inFin.addEventListener('change', checkSelects);

        selPresidente.addEventListener('change', (e) => {
            const pId = e.target.value;
            if (pId) {
                const pres = periodosPoliticos.presidentes.find(p => p.id === pId);
                inInicio.value = pres.inicio;
                inFin.value = pres.fin;
            } else {
                inInicio.value = '';
                inFin.value = '';
            }
            checkSelects();
        });

        btnLimpiar.addEventListener('click', () => {
            inInicio.value = '';
            inFin.value = '';
            selPresidente.value = '';
            selDepto.value = '';
            selCiudad.value = '';
            checkSelects();
            panelContextual.classList.add('hidden');
            // Resetear grafo
            if (window.filtrarGrafoPorFecha) window.filtrarGrafoPorFecha(null, null);

            // Eliminar event listeners duplicados de los botones de filtro antes de re-hacer renderNarrativas
            const oldFiltros = document.querySelector('.narrativas-filtros');
            if (oldFiltros) {
                const newFiltros = oldFiltros.cloneNode(true);
                oldFiltros.parentNode.replaceChild(newFiltros, oldFiltros);
            }

            // Remarcar botón Todos
            document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.filtro-btn[data-tipo="all"]')?.classList.add('active');

            // Re-render original
            renderNarrativas(allNarrativas);
        });

        btnAplicar.addEventListener('click', () => {
            const fInicio = inInicio.value;
            const fFin = inFin.value;
            const dpto = selDepto.value;
            const ciud = selCiudad.value;

            // Mostrar contexto si hay fechas
            if (fInicio || fFin) {
                gobernantesGrid.innerHTML = '';

                // Buscar presidente a mitad del periodo seleccionado (para simplificar si hay rango manual)
                let checkDate = fInicio || fFin;
                if (fInicio && fFin) {
                    // Si hay rango, tratar de encontrar el gobernante al inicio del periodo para no complicar
                    checkDate = fInicio;
                }
                const pres = politicosUtils.getPresidenteByDate(checkDate);

                if (pres) {
                    gobernantesGrid.innerHTML += `
                        <div class="gobernante-card">
                            <div class="gobernante-icon">🇨🇴</div>
                            <div class="gobernante-info">
                                <h4>Presidente</h4>
                                <h3>${pres.nombre}</h3>
                                <p>${pres.inicio.split('-')[0]} a ${pres.fin.split('-')[0]}</p>
                            </div>
                        </div>
                    `;
                }

                if (dpto) {
                    const gob = politicosUtils.getGobernadorByDate(dpto, checkDate);
                    gobernantesGrid.innerHTML += `
                        <div class="gobernante-card">
                            <div class="gobernante-icon">🏛️</div>
                            <div class="gobernante-info">
                                <h4>Gobernador / ${dpto}</h4>
                                <h3>${gob ? gob.nombre : 'No registrado para fecha'}</h3>
                                <p>${gob ? gob.inicio.split('-')[0] + ' a ' + gob.fin.split('-')[0] : 'Intente otra fecha'}</p>
                            </div>
                        </div>
                    `;
                }

                if (ciud) {
                    const alc = politicosUtils.getAlcaldeByDate(ciud, checkDate);
                    gobernantesGrid.innerHTML += `
                        <div class="gobernante-card">
                            <div class="gobernante-icon">🏙️</div>
                            <div class="gobernante-info">
                                <h4>Alcalde / ${ciud}</h4>
                                <h3>${alc ? alc.nombre : 'No registrado para fecha'}</h3>
                                <p>${alc ? alc.inicio.split('-')[0] + ' a ' + alc.fin.split('-')[0] : 'Intente otra fecha'}</p>
                            </div>
                        </div>
                    `;
                }

                if (gobernantesGrid.children.length > 0) {
                    panelContextual.classList.remove('hidden');
                } else {
                    panelContextual.classList.add('hidden');
                }
            } else {
                panelContextual.classList.add('hidden');
            }

            // Filtrar datos
            let filtered = politicosUtils.filterByPeriodo(allNarrativas, 'fecha', fInicio, fFin);

            // Eliminar event listeners duplicados haciendo clon del parent de botones
            const oldFiltros = document.querySelector('.narrativas-filtros');
            if (oldFiltros) {
                const newFiltros = oldFiltros.cloneNode(true);
                oldFiltros.parentNode.replaceChild(newFiltros, oldFiltros);
            }

            // Re-render narrativas
            renderNarrativas(filtered);

            // Filtrar el grafo por el mismo rango de fechas
            if (window.filtrarGrafoPorFecha) window.filtrarGrafoPorFecha(fInicio, fFin);

            // Scrollear a los resultados de manera suave
            document.getElementById('periodistas').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    };

    // ── Menú hamburguesa (mobile) ────────────────────────────────────────────────
    const hamburger = document.getElementById('nav-hamburger');
    const navLinks  = document.getElementById('nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            const isOpen = navLinks.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', String(isOpen));
            hamburger.setAttribute('aria-label', isOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación');
        });
        // Cerrar menú al hacer click en un enlace
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('open');
                hamburger.setAttribute('aria-expanded', 'false');
                hamburger.setAttribute('aria-label', 'Abrir menú de navegación');
            });
        });
    }

    // Init
    loadData();
    setupDownloadBtn();
});
