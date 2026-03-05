document.addEventListener('DOMContentLoaded', () => {

    // Iniciar D3 Graph
    const initGraph = async () => {
        try {
            const res = await fetch(`data/grafo_red.json?v=${Date.now()}`);
            const data = await res.json();

            drawGraph(data);
        } catch (error) {
            console.error("Error cargando grafo:", error);
            document.getElementById('d3-graph').innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-secondary);">No se pudo cargar la visualización de red. Asegúrate de ejecutar el script de Python primero.</div>';
        }
    };

    const drawGraph = (data) => {
        const container = document.getElementById('d3-graph');
        const width = container.clientWidth;
        const height = container.clientHeight;

        container.innerHTML = ''; // Clear

        const svg = d3.select('#d3-graph').append('svg')
            .attr('width', width)
            .attr('height', height);

        // Contenedor para zoom
        const g = svg.append('g');

        // Zoom setup
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Botón Reset Zoom
        document.getElementById('reset-zoom').addEventListener('click', () => {
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
        });

        // Colores según grupo
        const colorScale = d3.scaleOrdinal()
            .domain([1, 2, 3])
            .range(['#388bfd', '#fb8500', '#e63946']); // Azul(Entidad), Naranja(Contratista), Rojo(Persona)

        // Simulation
        const simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collide', d3.forceCollide().radius(d => Math.sqrt(d.val || 1) * 3 + 10));

        // Links
        const link = g.append('g')
            .selectAll('line')
            .data(data.links)
            .enter().append('line')
            .attr('stroke', '#30363d')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.max(1, Math.sqrt(d.value) * 0.5));

        // Nodes
        const node = g.append('g')
            .selectAll('circle')
            .data(data.nodes)
            .enter().append('circle')
            .attr('r', d => Math.max(5, Math.min(30, Math.sqrt(d.val || 1) * 3)))
            .attr('fill', d => colorScale(d.group))
            .attr('stroke', '#0d1117')
            .attr('stroke-width', 2)
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

        // Nombres en los nodos para los más grandes
        const labels = g.append('g')
            .selectAll('text')
            .data(data.nodes.filter(d => d.val > 20)) // Solo mostrar textos de nodos principales para no saturar
            .enter().append('text')
            .attr('dx', 12)
            .attr('dy', '.35em')
            .text(d => {
                const parts = d.name.split(' ');
                if (d.group === 3 && parts.length > 1) {
                    return `${parts[0][0]}. ${parts[parts.length - 1]}`; // Inicial + Apellido
                }
                return d.name.length > 20 ? d.name.substring(0, 20) + '...' : d.name;
            })
            .attr('font-size', '10px')
            .attr('fill', '#8b949e')
            .style('pointer-events', 'none');

        // Tooltip básico hover
        const tooltip = document.getElementById('tooltip');

        node.on('mouseover', (event, d) => {
            tooltip.innerHTML = `<strong>${d.name}</strong><br><span class="text-secondary">${d.label}</span>`;
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top = (event.pageY + 10) + 'px';
            tooltip.classList.remove('hidden');

            // Highlight connections
            link.style('stroke', l => l.source.id === d.id || l.target.id === d.id ? '#58a6ff' : '#30363d')
                .style('stroke-opacity', l => l.source.id === d.id || l.target.id === d.id ? 1 : 0.2);
        })
            .on('mouseout', () => {
                tooltip.classList.add('hidden');
                link.style('stroke', '#30363d').style('stroke-opacity', 0.6);
            })
            .on('click', (event, d) => {
                openSidebar(d, data.links);
            });

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            labels
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        // Lógica filtro rango
        const slider = document.getElementById('value-filter');
        slider.addEventListener('input', (e) => {
            const threshold = parseInt(e.target.value);
            // Hide nodes that have val < threshold (unless threshold is 0)
            node.style('display', d => d.val >= threshold ? 'block' : 'none');
            // Hide links if source or target are hidden
            link.style('display', l => l.source.val >= threshold && l.target.val >= threshold ? 'block' : 'none');
            labels.style('display', d => d.val >= threshold ? 'block' : 'none');
            // Reheat simulation
            simulation.alphaTarget(0.1).restart();
            setTimeout(() => simulation.alphaTarget(0), 1000);
        });

        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
    };

    // UI de la barra lateral al clickear nodo
    const sidebar = document.getElementById('node-sidebar');
    const closeBtn = document.querySelector('.close-sidebar');
    const sidebarDetails = document.getElementById('sidebar-details');

    closeBtn.addEventListener('click', () => {
        sidebar.classList.add('hidden');
    });

    const openSidebar = (nodeInfo, allLinks) => {
        // Encontrar conexiones
        const connectedLinks = allLinks.filter(l => l.source.id === nodeInfo.id || l.target.id === nodeInfo.id);

        let html = `
            <h3>${nodeInfo.name}</h3>
            <p><strong>Tipo:</strong> <span class="badge badge-orange">${nodeInfo.label}</span></p>
            <p><strong>Impacto Relativo:</strong> ${Math.round(nodeInfo.val)}</p>
            <h4 style="margin-top:20px; font-size:1rem;">Conexiones Detectadas (${connectedLinks.length})</h4>
            <ul class="link-list">
        `;

        if (connectedLinks.length === 0) {
            html += `<li>Sin conexiones directas en este subgrafo.</li>`;
        } else {
            connectedLinks.forEach(l => {
                const isTarget = l.target.id === nodeInfo.id;
                const otherNode = isTarget ? l.source : l.target;
                const verb = l.type === 'ORDENÓ' ? (isTarget ? 'Recibió orden de' : 'Ordenó a') :
                    l.type === 'SOBRECOSTO' ? (isTarget ? 'Sobrecostos para' : 'Generó sobrecosto a') :
                        isTarget ? 'Vinculado desde' : 'Vinculado hacia';

                const valStr = l.value > 0 ? `$${parseFloat(l.value).toLocaleString('es-CO')}B COP` : 'Relación Estructural';

                html += `<li>
                    <span style="color:var(--text-secondary); font-size:0.8em;">[${l.type}]</span><br>
                    ${verb} <strong>${otherNode.name}</strong><br>
                    <span class="mono" style="color:var(--color-naranja);">${valStr}</span>
                </li>`;
            });
        }

        html += `</ul>`;

        sidebarDetails.innerHTML = html;
        sidebar.classList.remove('hidden');
    };

    // Initialize
    initGraph();
});
