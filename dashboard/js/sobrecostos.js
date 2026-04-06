// sobrecostos.js — Tabla sobrecostos/prórrogas
document.addEventListener('DOMContentLoaded', () => {

    const renderSobrecostosTable = (data) => {
        const tbody = document.querySelector('#table-sobrecostos tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        // Normalizar data-sort headers
        const sortMap = { entidad: 'entidad_nombre', contratista: 'contratista_nombre',
                          contrato_id: 'ct.id', dias_prorroga: 'ct.dias_adicionados', valor_m: 'ct.valor' };
        document.querySelectorAll('#table-sobrecostos th[data-sort]').forEach(th => {
            const k = th.getAttribute('data-sort');
            if (sortMap[k]) th.setAttribute('data-sort', sortMap[k]);
        });

        data.forEach(row => {
            const tr = document.createElement('tr');
            let td;

            td = document.createElement('td');
            const en = row.entidad_nombre || row.entidad || '';
            td.textContent = en && !en.startsWith('Entidad (NIT') ? en
                : (row.display_name && row.display_name !== 'Desconocido' ? row.display_name : 'Sin nombre');
            tr.appendChild(td);

            td = document.createElement('td');
            const cn = row.contratista_nombre || row.contratista || '';
            td.textContent = cn && !cn.startsWith('Contratista (DOC') ? cn
                : (row.display_name && row.display_name !== 'Desconocido' ? row.display_name : 'Sin nombre');
            tr.appendChild(td);

            td = document.createElement('td');
            td.className = 'mono';
            td.textContent = row['ct.id'] || row.contrato_id || 'N/A';
            tr.appendChild(td);

            td = document.createElement('td');
            const dias = parseInt(row['ct.dias_adicionados'] || row.dias_prorroga) || 0;
            td.innerHTML = `<span class="badge ${dias > 365 ? 'badge-red' : 'badge-orange'}">${dias.toLocaleString('es-CO')} días</span>`;
            tr.appendChild(td);

            td = document.createElement('td');
            const valorCOP = parseFloat(row['ct.valor']) || 0;
            const valorB   = valorCOP / 1e12;
            const valorM   = valorCOP / 1e6;
            if (valorB >= 0.001) {
                td.innerHTML = `<strong>$${valorB.toLocaleString('es-CO', { minimumFractionDigits: 3 })}B COP</strong>
                    <div class="valor-usd">${formatUSD(valorB)}</div>`;
            } else {
                td.innerHTML = `<strong>$${Math.round(valorM).toLocaleString('es-CO')} M COP</strong>
                    <div class="valor-usd">${formatUSD(valorB)}</div>`;
            }
            tr.appendChild(td);

            td = document.createElement('td');
            const obj = row['ct.objeto'] || row.objeto || 'Sin descripción';
            td.textContent = obj.length > 60 ? obj.substring(0, 60) + '…' : obj;
            if (obj.length > 60) td.title = obj;
            tr.appendChild(td);

            tbody.appendChild(tr);
        });

        setupTableSorting('table-sobrecostos', data,
            ['entidad_nombre','contratista_nombre','ct.id','ct.dias_adicionados','ct.valor'],
            false, renderSobrecostosTable);
    };

    const init = async () => {
        try {
            renderSobrecostosTable(await fetchDashboardJSON('sobrecostos.json'));
        } catch (e) {
            console.error('Error cargando sobrecostos:', e);
        }
    };

    init();
});
