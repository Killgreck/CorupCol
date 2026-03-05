import json
import logging
from datetime import datetime
import os
from grafo.queries.anomalias import run_anomaly_queries
from grafo.queries.stats import get_graph_stats

logger = logging.getLogger(__name__)

def generar_reporte():
    logger.info("Comenzando generación de reporte JSON...")
    
    stats = get_graph_stats()
    
    anomalias = run_anomaly_queries()
    
    report_data = {
        "metadata": {
            "fecha_generacion": datetime.now().isoformat(),
            "estadisticas_generales": {
                "total_nodos": stats.get("total_nodos", 0),
                "total_relaciones": stats.get("total_relaciones", 0),
                "valor_total_contratos": stats.get("valor_total_contratos", 0.0)
            }
        },
        "top_resumenes": {
            "top_20_contratistas_por_valor": stats.get("top_20_contratistas_acumulado", []),
            "top_20_entidades_unico_oferente": stats.get("top_20_entidades_unico_oferente", []),
            "top_20_recurrentes_ordenador_contratista": stats.get("top_20_ordenador_contratista", [])
        },
        "anomalias": anomalias
    }
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
    os.makedirs(output_dir, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_path = os.path.join(output_dir, f"anomalias_{today_str}.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Reporte guardado en: {report_path}")
    return report_path
