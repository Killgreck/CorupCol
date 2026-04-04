document.addEventListener('DOMContentLoaded', () => {

    // ── Estado del módulo ────────────────────────────────────────────────────────
    let _node, _link, _labels, _allData, _simulation;

    // Escapa caracteres HTML para prevenir XSS al inyectar datos del grafo en innerHTML
    const escapeHtml = (str) => {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    // ── Cargar y dibujar ─────────────────────────────────────────────────────────
    const initGraph = async () => {
        try {
            const res = await fetch('/static_dashboard/data/grafo_red.json');
            _allData = await res.json();
            drawGraph(_allData);
        } catch (error) {
            console.error("Error cargando grafo:", error);
            document.getElementById('d3-graph').innerHTML =
                '<div style="padding:20px;text-align:center;color:var(--text-secondary);">No se pudo cargar la red. Ejecuta primero preparar_datos_publicos.py</div>';
        }
    };

    const drawGraph = (data) => {
        const container = document.getElementById('d3-graph');
        const width  = container.clientWidth;
        const height = container.clientHeight;
        container.innerHTML = '';

        const svg = d3.select('#d3-graph').append('svg')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g');

        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => { g.attr('transform', event.transform); });
        svg.call(zoom);

        document.getElementById('reset-zoom').addEventListener('click', () => {
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
        });

        const colorScale = d3.scaleOrdinal()
            .domain([1, 2, 3])
            .range(['#388bfd', '#fb8500', '#e63946']);

        _simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collide', d3.forceCollide().radius(d => Math.sqrt(d.val || 1) * 3 + 10));

        _link = g.append('g').selectAll('line')
            .data(data.links).enter().append('line')
            .attr('stroke', '#30363d')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.max(1, Math.sqrt(d.value) * 0.5));

        _node = g.append('g').selectAll('circle')
            .data(data.nodes).enter().append('circle')
            .attr('r', d => Math.max(5, Math.min(30, Math.sqrt(d.val || 1) * 3)))
            .attr('fill', d => colorScale(d.group))
            .attr('stroke', '#0d1117')
            .attr('stroke-width', 2)
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) _simulation.alphaTarget(0.3).restart();
                    d.fx = d.x; d.fy = d.y;
                })
                .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
                .on('end', (event, d) => {
                    if (!event.active) _simulation.alphaTarget(0);
                    d.fx = null; d.fy = null;
                }));

        _labels = g.append('g').selectAll('text')
            .data(data.nodes.filter(d => d.val > 20)).enter().append('text')
            .attr('dx', 12).attr('dy', '.35em')
            .text(d => {
                const parts = d.name.split(' ');
                if (d.group === 3 && parts.length > 1)
                    return `${parts[0][0]}. ${parts[parts.length - 1]}`;
                return d.name.length > 20 ? d.name.substring(0, 20) + '…' : d.name;
            })
            .attr('font-size', '10px')
            .attr('fill', '#8b949e')
            .style('pointer-events', 'none');

        const tooltip = document.getElementById('tooltip');

        _node.on('mouseover', (event, d) => {
            tooltip.innerHTML = `<strong>${escapeHtml(d.name)}</strong><br>
                <span class="text-secondary">${escapeHtml(d.label)}</span>
                ${d.fecha ? `<br><span style="color:var(--color-azul);font-size:0.8em;">${escapeHtml(d.fecha)}</span>` : ''}`;
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top  = (event.pageY + 10) + 'px';
            tooltip.classList.remove('hidden');
            _link.style('stroke', l =>
                l.source.id === d.id || l.target.id === d.id ? '#58a6ff' : '#30363d')
                .style('stroke-opacity', l =>
                    l.source.id === d.id || l.target.id === d.id ? 1 : 0.2);
        })
        .on('mouseout', () => {
            tooltip.classList.add('hidden');
            _link.style('stroke', '#30363d').style('stroke-opacity', 0.6);
        })
        .on('click', (event, d) => { openSidebar(d, data.links); });

        _simulation.on('tick', () => {
            _link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                 .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
            _node.attr('cx', d => d.x).attr('cy', d => d.y);
            _labels.attr('x', d => d.x).attr('y', d => d.y);
        });

        // Filtro por relevancia (slider existente)
        document.getElementById('value-filter').addEventListener('input', (e) => {
            const thr = parseInt(e.target.value);
            _node.style('display',   d => d.val >= thr ? 'block' : 'none');
            _link.style('display',   l => l.source.val >= thr && l.target.val >= thr ? 'block' : 'none');
            _labels.style('display', d => d.val >= thr ? 'block' : 'none');
            _simulation.alphaTarget(0.1).restart();
            setTimeout(() => _simulation.alphaTarget(0), 1000);
        });
    };

    // ── Filtrado por rango de fechas (llamado desde main.js) ─────────────────────
    //
    // Nodos SIN fecha (carrusel/nepotismo) → SIEMPRE visibles.
    // Nodos CON fecha (empresa reciente / autocontratación) → solo si caen en rango.
    //
    window.filtrarGrafoPorFecha = (inicio, fin) => {
        if (!_node || !_allData) return;

        const startDate = inicio ? new Date(inicio) : null;
        const endDate   = fin   ? new Date(fin)    : null;

        const visible = (d) => {
            if (!d.fecha) return true;          // sin fecha → siempre
            const t = new Date(d.fecha);
            if (startDate && t < startDate) return false;
            if (endDate   && t > endDate)   return false;
            return true;
        };

        // Construir set de IDs visibles
        const visSet = new Set(_allData.nodes.filter(visible).map(n => n.id));

        _node.transition().duration(400)
            .style('opacity', d => visSet.has(d.id) ? 1 : 0.1)
            .style('pointer-events', d => visSet.has(d.id) ? 'auto' : 'none');

        _link.transition().duration(400)
            .style('opacity', l => {
                const sId = typeof l.source === 'object' ? l.source.id : l.source;
                const tId = typeof l.target === 'object' ? l.target.id : l.target;
                return visSet.has(sId) && visSet.has(tId) ? 0.6 : 0.05;
            });

        _labels.transition().duration(400)
            .style('opacity', d => visSet.has(d.id) ? 1 : 0);

        // Indicador visual en la sección del grafo
        const notice = document.getElementById('grafo-fecha-notice');
        if (notice) {
            if (inicio || fin) {
                const txt = [inicio, fin].filter(Boolean).join(' → ');
                notice.textContent = `Mostrando nodos con fecha en: ${txt}. Nodos sin fecha siempre visibles.`;
                notice.classList.remove('hidden');
            } else {
                notice.classList.add('hidden');
            }
        }
    };

    // ── Sidebar al hacer click en nodo ───────────────────────────────────────────
    const sidebar      = document.getElementById('node-sidebar');
    const closeBtn     = document.querySelector('.close-sidebar');
    const sidebarDetails = document.getElementById('sidebar-details');

    closeBtn.addEventListener('click', () => sidebar.classList.add('hidden'));

    const openSidebar = (nodeInfo, allLinks) => {
        const connectedLinks = allLinks.filter(
            l => l.source.id === nodeInfo.id || l.target.id === nodeInfo.id
        );

        let html = `
            <h3>${escapeHtml(nodeInfo.name)}</h3>
            <p><strong>Tipo:</strong> <span class="badge badge-orange">${escapeHtml(nodeInfo.label)}</span></p>
            ${nodeInfo.fecha ? `<p><strong>Fecha:</strong> <span style="color:var(--color-azul)">${escapeHtml(nodeInfo.fecha)}</span></p>` : ''}
            <p><strong>Impacto Relativo:</strong> ${Math.round(nodeInfo.val)}</p>
            <h4 style="margin-top:20px;font-size:1rem;">Conexiones (${connectedLinks.length})</h4>
            <ul class="link-list">`;

        if (!connectedLinks.length) {
            html += `<li>Sin conexiones directas en este subgrafo.</li>`;
        } else {
            connectedLinks.forEach(l => {
                const isTarget  = l.target.id === nodeInfo.id;
                const other     = isTarget ? l.source : l.target;
                const verb      = l.type === 'ORDENÓ'
                    ? (isTarget ? 'Recibió orden de' : 'Ordenó a')
                    : l.type === 'SOBRECOSTO'
                    ? (isTarget ? 'Sobrecosto hacia' : 'Generó sobrecosto a')
                    : (isTarget ? 'Vinculado desde'  : 'Vinculado hacia');
                const valStr = l.value > 0
                    ? `$${parseFloat(l.value).toLocaleString('es-CO')}B COP`
                    : 'Relación estructural';
                html += `<li>
                    <span style="color:var(--text-secondary);font-size:0.8em;">[${escapeHtml(l.type)}]</span><br>
                    ${escapeHtml(verb)} <strong>${escapeHtml(other.name)}</strong><br>
                    <span class="mono" style="color:var(--color-naranja);">${escapeHtml(valStr)}</span>
                </li>`;
            });
        }
        html += `</ul>`;
        sidebarDetails.innerHTML = html;
        sidebar.classList.remove('hidden');
    };

    initGraph();
});
