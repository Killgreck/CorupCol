document.addEventListener('DOMContentLoaded', () => {

    // ── Tasa de cambio USD/COP ───────────────────────────────────────────────────
    let _usdRate = 4200; // fallback hasta que llegue la tasa real

    const fetchUSDRate = async () => {
        try {
            const res = await fetch('https://open.er-api.com/v6/latest/USD');
            const data = await res.json();
            if (data.rates?.COP) {
                _usdRate = data.rates.COP;
                window._usdRate = _usdRate;
            }
        } catch (_) { /* usa el fallback */ }
        return _usdRate;
    };

    // Formatea billones COP → USD con sufijo T/B/M inteligente
    const formatUSD = (billonesCOP) => {
        const rate = window._usdRate || _usdRate;
        const usd = billonesCOP * 1e12 / rate;
        if (usd >= 1e12) return `≈ USD ${(usd / 1e12).toFixed(2)} T`;
        if (usd >= 1e9) return `≈ USD ${(usd / 1e9).toFixed(1)} B`;
        if (usd >= 1e6) return `≈ USD ${(usd / 1e6).toFixed(1)} M`;
        return `≈ USD ${(usd / 1e3).toFixed(0)} K`;
    };

    // Inicia la carga de tasa en paralelo (no bloquea el dashboard)
    fetchUSDRate();

    // 1. Cargar datos
    const loadData = async () => {
        try {
            const v = Date.now();
            const [statsRes, carruselRes, nepotismoRes, sobrecostosRes, narrativasRes, timelinesRes] = await Promise.all([
                fetch(`data/stats.json?v=${v}`),
                fetch(`data/carrusel.json?v=${v}`),
                fetch(`data/nepotismo.json?v=${v}`),
                fetch(`data/sobrecostos.json?v=${v}`),
                fetch(`data/narrativas.json?v=${v}`),
                fetch(`data/timelines.json?v=${v}`).catch(() => ({ json: () => ({}) }))
            ]);

            const stats = await statsRes.json();
            const carrusel = await carruselRes.json();
            const nepotismo = await nepotismoRes.json();
            const sobrecostos = await sobrecostosRes.json();
            const narrativas = await narrativasRes.json();

            // Cargar timelines de forma segura para no romper la app si falla
            window._timelines = {};
            try {
                if (timelinesRes && timelinesRes.ok) {
                    window._timelines = await timelinesRes.json();
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
            document.getElementById('counter-contratos').textContent = "Error";
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

        // Mostrar USD tras obtener la tasa real (espera a tenerla)
        const rate = await fetchUSDRate();
        const usdEl = document.getElementById('counter-valor-usd');
        if (usdEl) {
            const usd = stats.valor_total_b * 1e12 / rate;
            const usdT = (usd / 1e12).toFixed(2);
            usdEl.textContent = `≈ USD ${usdT} T`;
            usdEl.title = `Tasa en tiempo real: 1 USD = ${rate.toFixed(0)} COP`;
        }
    };

    const animateValue = (id, start, end, duration, noDecimals = false, prefix = '', suffix = '') => {
        const obj = document.getElementById(id);
        if (!obj) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // ease out cubic
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = (progress * (end - start) + start);

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
            if (tableId === 'table-carrusel' && row['c.doc_id']) {
                tr.addEventListener('click', () => {
                    const nit = row['c.doc_id'];
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
                        title.textContent = `Línea de Tiempo de Contratación: ${row.display_name} (NIT: ${nit})`;

                        const canvas = document.createElement('canvas');
                        container.appendChild(title);
                        container.appendChild(canvas);
                        wrapper.appendChild(container);
                        chartTd.appendChild(wrapper);
                        chartTr.appendChild(chartTd);

                        tr.after(chartTr);

                        // Wait a tick to apply animation class
                        requestAnimationFrame(() => {
                            wrapper.classList.add('expanded');
                            renderTimelineGraph(canvas, nit);
                        });
                    }
                });
            }

            tbody.appendChild(tr);
        });

        setupTableSorting(tableId, data, columns, addValueBar);
    };

    // Renderizar gráfico con Chart.js
    const renderTimelineGraph = (canvas, nit) => {
        const timelines = window._timelines || {};
        const data = timelines[nit];

        if (!data || data.length === 0) {
            const ctx = canvas.getContext('2d');
            ctx.font = '14px Inter';
            ctx.fillStyle = '#8b949e';
            ctx.textAlign = 'center';
            ctx.fillText('No hay datos históricos disponibles', canvas.width / 2, canvas.height / 2);
            return;
        }

        const labels = data.map(d => d.fecha);
        const values = data.map(d => d.valor_total_b || 0);

        return new Chart(canvas, {
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
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(context.parsed.y * 1e12);
                                }
                                return label;
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
                }
            }
        });
    };

    // Modal: abre la gráfica de contratos en el tiempo para un NIT
    const openTimelineModal = (nit, nombre) => {
        const modal = document.getElementById('timeline-modal');
        document.getElementById('timeline-modal-title').textContent = `${nombre} · NIT ${nit}`;

        if (window._modalChart) {
            window._modalChart.destroy();
            window._modalChart = null;
        }

        // Reemplazar canvas para evitar el error "Canvas is already in use"
        const oldCanvas = document.getElementById('timeline-modal-canvas');
        const newCanvas = document.createElement('canvas');
        newCanvas.id = 'timeline-modal-canvas';
        oldCanvas.parentNode.replaceChild(newCanvas, oldCanvas);

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        window._modalChart = renderTimelineGraph(newCanvas, nit);
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
                return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank">${n.contrato_id || ''}</a> en Colombia Compra Eficiente y compara "Ordenador del gasto" con "Representante legal".`;
            } else if (tipo === 'nepotismo') {
                return `<strong>Cómo verificarlo:</strong> Busca la cédula <code>${n.doc_ordenador || ''}</code> como ordenador en el buscador avanzado del SECOP II y filtra por contratista.`;
            } else if (tipo === 'carrusel') {
                return `<strong>Cómo verificarlo:</strong> Busca el NIT <code>${n.doc_id || ''}</code> en <a href="${SECOP_URL}" target="_blank">SECOP II</a> y revisa las entidades que lo han contratado.`;
            } else {
                return `<strong>Cómo verificarlo:</strong> Busca el contrato <a href="${SECOP_URL}" target="_blank">${n.contrato_id || ''}</a> en Colombia Compra Eficiente y revisa las modificaciones.`;
            }
        };

        const fmtFecha = (iso) => {
            if (!iso) return null;
            const [y, m, d] = iso.split('-');
            return `${d}/${m}/${y}`;
        };

        const buildMeta = (n) => {
            const chips = [];
            const nombre = n.funcionario || n.ordenador || n.contratista || n.entidad || '';
            if (nombre) chips.push(nombre.length > 35 ? nombre.slice(0, 35) + '…' : nombre);
            if (n.valor_m) chips.push(`$${(n.valor_m / 1000).toFixed(1)}B COP`);
            if (n.valor_b) chips.push(`$${n.valor_b}B COP`);
            if (n.contratos) chips.push(`${n.contratos} contratos`);
            if (n.entidades) chips.push(`${n.entidades} entidades`);
            if (n.dias_prorroga) chips.push(`${n.dias_prorroga} días prórroga`);

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
                const lbl = LABELS[n.tipo] || { icon: '📋', texto: n.tipo };
                const nit = n.doc_id || '';
                const nombre = (n.contratista || n.funcionario || n.entidad || 'Caso detectado').replace(/"/g, '&quot;');
                return `
                <div class="narrativa-card tipo-${n.tipo}" data-tipo="${n.tipo}" data-nit="${nit}" data-nombre="${nombre}">
                    <span class="narrativa-badge ${n.tipo}">${lbl.icon} ${lbl.texto}</span>
                    <div class="narrativa-titulo">${n.funcionario || n.contratista || n.entidad || 'Caso detectado'}</div>
                    <div class="narrativa-meta">${buildMeta(n)}</div>
                    <p class="narrativa-texto">${n.narrativa}</p>
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

        data.forEach(row => {
            const tr = document.createElement('tr');

            // Entidad
            let td = document.createElement('td');
            td.textContent = row.entidad || row.entidad_nombre || 'N/A';
            tr.appendChild(td);

            // Contratista
            td = document.createElement('td');
            td.textContent = row.contratista || row.contratista_nombre || 'N/A';
            tr.appendChild(td);

            // ID
            td = document.createElement('td');
            td.className = 'mono';
            td.textContent = row.contrato_id || row['ct.id'] || 'N/A';
            tr.appendChild(td);

            // Días extra con badge
            td = document.createElement('td');
            const dias = parseInt(row.dias_prorroga || row['ct.dias_adicionados']) || 0;
            let badgeClass = 'badge-orange';
            if (dias > 365) badgeClass = 'badge-red';
            td.innerHTML = `<span class="badge ${badgeClass}">${dias} días</span>`;
            tr.appendChild(td);

            // Valor (valor_m = millones, valor_b = billones)
            td = document.createElement('td');
            const val = row.valor_m ? row.valor_m / 1000 : (parseFloat(row['ct.valor_b']) || 0);
            td.innerHTML = `<strong>$${val.toLocaleString('es-CO', { minimumFractionDigits: 1 })}B COP</strong>
                <div class="valor-usd">${formatUSD(val)}</div>`;
            tr.appendChild(td);

            // Objeto (truncado con tooltip)
            td = document.createElement('td');
            const objTxt = row.objeto || row['ct.objeto'] || 'Sin descripción';
            if (objTxt.length > 50) {
                td.textContent = objTxt.substring(0, 50) + '...';
                td.title = objTxt; // nativo tooltip
            } else {
                td.textContent = objTxt;
            }
            tr.appendChild(td);

            tbody.appendChild(tr);
        });

        setupTableSorting('table-sobrecostos', data, ['entidad', 'contratista', 'contrato_id', 'dias_prorroga', 'valor_m'], false, renderSobrecostosTable);
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
                resultsContainer.innerHTML = '<div class="search-item"><div class="search-item-title text-secondary">No se encontraron resultados para "' + query + '"</div></div>';
            } else {
                results.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'search-item';

                    let title = '';
                    let desc = '';
                    let badgeClass = '';

                    if (item._type === 'Carrusel') {
                        title = item.display_name || 'Desconocido';
                        desc = `NIT: ${item['c.doc_id'] || 'N/A'} - ${item.entidades_distintas} Entidades - ${item.total_contratos} Contratos`;
                        badgeClass = 'badge-carrusel';
                    } else if (item._type === 'Nepotismo') {
                        title = `${item.p?.nombre_display || item['p.nombre']} ↔ ${item._nombre_contratista_display || item.display_name}`;
                        desc = `CC: ${item['p.doc_id'] || 'N/A'} - Contratos juntos: ${item.contratos_juntos}`;
                        badgeClass = 'badge-nepotismo';
                    } else if (item._type === 'Sobrecosto') {
                        title = item.contratista || item.contratista_nombre || 'Desconocido';
                        desc = `ID: ${item.contrato_id || item['ct.id']} - ${item.dias_prorroga || item['ct.dias_adicionados']} días extra - Entidad: ${item.entidad || item.entidad_nombre}`;
                        badgeClass = 'badge-sobrecosto';
                    }

                    div.innerHTML = `
                        <div>
                            <div class="search-item-title">${title} <span class="badge ${badgeClass}">${item._type}</span></div>
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
                    fetch('data/carrusel.json'),
                    fetch('data/nepotismo.json'),
                    fetch('data/sobrecostos.json')
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

    // Init
    loadData();
    setupDownloadBtn();
});
