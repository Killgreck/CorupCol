// index.js — Landing: stats animados, donut presupuesto, descarga ZIP
document.addEventListener('DOMContentLoaded', () => {

    const animateValue = (id, start, end, duration, noDecimals = false, prefix = '', suffix = '') => {
        const obj = document.getElementById(id);
        if (!obj) return;
        let t0 = null;
        const step = (ts) => {
            if (!t0) t0 = ts;
            const p = Math.min((ts - t0) / duration, 1);
            const ease = 1 - Math.pow(1 - p, 3);
            const cur = ease * (end - start) + start;
            obj.textContent = noDecimals
                ? prefix + Math.floor(cur).toLocaleString('es-CO') + suffix
                : prefix + cur.toLocaleString('es-CO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + suffix;
            if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    };

    const renderBudgetChart = (stats) => {
        const wrapper = document.getElementById('budget-chart-wrapper');
        const canvas  = document.getElementById('budget-donut-chart');
        if (!wrapper || !canvas) return;
        wrapper.classList.remove('hidden');
        void wrapper.offsetHeight; // reflow síncrono antes de que Chart.js mida

        const total      = parseFloat(stats.valor_total_b) || 0;
        const carrusel   = parseFloat(stats.total_val_carrusel_b) || 0;
        const nepotismo  = parseFloat(stats.total_val_nepotismo_b) || 0;
        const sobrec     = parseFloat(stats.total_val_sobrecostos_b) || 0;
        const resto      = Math.max(0, total - carrusel - nepotismo - sobrec);

        new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Contratación Estándar', 'Carrusel de Contratos', 'Asignación Repetitiva', 'Sobrecostos Prórroga'],
                datasets: [{
                    data: [resto, carrusel, nepotismo, sobrec],
                    backgroundColor: ['#2ea043', '#d29922', '#f0883e', '#da3633'],
                    borderColor: '#0d1117', borderWidth: 2, hoverOffset: 6
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, color: '#c9d1d9',
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#8b949e', padding: 20, font: { family: 'Inter', size: 12 } } },
                    tooltip: {
                        backgroundColor: 'rgba(22,27,34,.95)', titleColor: '#c9d1d9',
                        bodyColor: '#e6edf3', borderColor: '#30363d', borderWidth: 1,
                        callbacks: {
                            label: (ctx) => {
                                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return `${ctx.label}: $${ctx.parsed.toLocaleString('es-CO', { minimumFractionDigits: 1 })}B COP (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    };

    const loadStats = async () => {
        ['counter-contratos', 'counter-valor', 'counter-anomalias'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '…';
        });
        try {
            const stats = await fetchDashboardJSON('stats.json');

            animateValue('counter-contratos', 0, stats.total_contratos, 2000, true);
            animateValue('counter-valor', 0, stats.valor_total_b, 2000, false, '$', 'B');
            animateValue('counter-anomalias', 0,
                (stats.casos_carrusel || 0) + (stats.casos_nepotismo || 0) +
                (stats.casos_sobrecosto || 0) + (stats.casos_autocontratacion || 0), 2000, true);

            const safe = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
            safe('finding-carrusel', stats.casos_carrusel);
            safe('finding-nepotismo', stats.casos_nepotismo);
            safe('finding-sobrecostos', stats.casos_sobrecosto);
            safe('footer-date', (stats.fecha || '').split('T')[0]);

            if (stats.presupuesto_origen_nota) {
                const el = document.getElementById('budget-source');
                if (el) el.textContent = `📝 Origen: ${stats.presupuesto_origen_nota}`;
            }

            const rate = await fetchUSDRate();
            const usdEl = document.getElementById('counter-valor-usd');
            if (usdEl) {
                usdEl.textContent = `≈ USD ${(stats.valor_total_b * 1e12 / rate / 1e12).toFixed(2)} T`;
                usdEl.title = `Tasa: 1 USD = ${rate.toFixed(0)} COP`;
            }

            renderBudgetChart(stats);
        } catch (e) {
            console.error('Error cargando stats:', e);
            ['counter-contratos', 'counter-valor', 'counter-anomalias'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = '—';
            });
        }
    };

    // Descarga ZIP desde la landing
    const btn = document.getElementById('btn-download');
    if (btn && typeof JSZip !== 'undefined') {
        btn.addEventListener('click', async () => {
            btn.innerHTML = '<span class="btn-icon">⏳</span> Generando ZIP…';
            btn.disabled = true;
            try {
                const [cr, nr, sr] = await Promise.all([
                    fetchDashboardJSON('carrusel.json'),
                    fetchDashboardJSON('nepotismo.json'),
                    fetchDashboardJSON('sobrecostos.json')
                ]);
                const toCSV = (data, keys) => keys.join(',') + '\n' + data.map(obj =>
                    keys.map(k => {
                        let c = obj[k] === null || obj[k] === undefined ? '' : String(obj[k]);
                        c = c.replace(/"/g, '""');
                        if (/("|,|\n)/.test(c)) c = `"${c}"`;
                        return c;
                    }).join(',')
                ).join('\n');
                const zip = new JSZip();
                zip.file('carruseles.csv', toCSV(cr, ['display_name','c.doc_id','entidades_distintas','total_contratos','total_valor','total_valor_b']));
                zip.file('nepotismo.csv',  toCSV(nr, ['p.nombre','p.doc_id','display_name','c.doc_id','contratos_juntos','valor_total','valor_total_b']));
                zip.file('sobrecostos.csv',toCSV(sr, ['entidad','contratista','contrato_id','dias_prorroga','valor_m','objeto']));
                const content = await zip.generateAsync({ type: 'blob' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(content);
                a.download = `CorupCol_${new Date().toISOString().split('T')[0]}.zip`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
                btn.innerHTML = '<span class="btn-icon">✅</span> ¡Descargado!';
                setTimeout(() => { btn.innerHTML = '<span class="btn-icon">📦</span> Descargar Todos los Datos (ZIP)'; btn.disabled = false; }, 3000);
            } catch (err) {
                console.error(err);
                btn.innerHTML = '<span class="btn-icon">❌</span> Error. Intenta de nuevo.';
                btn.disabled = false;
            }
        });
    }

    loadStats();
});
