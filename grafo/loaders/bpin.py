import os
import logging
from grafo.config import DATA_DIR
from grafo.loaders.base_loader import load_csv_in_batches

logger = logging.getLogger(__name__)

def load_bpin():
    filepath = os.path.join(DATA_DIR, 'bpin.csv')
    if not os.path.exists(filepath):
        logger.warning(f"Archivo {filepath} no existe, omitiendo carga de bpin.")
        return 0

    query = """
    UNWIND $batch AS row
    
    MERGE (pi:ProyectoInversion {codigo_bpin: coalesce(row.codigo_bpin, row.bpin)})
    ON CREATE SET
        pi.anno = coalesce(row.anno, row.anio, substring(row.fecha, 0, 4)),
        pi.id_portafolio = coalesce(row.id_portafolio, "Desconocido")

    WITH pi, row
    FOREACH (cid IN CASE WHEN row.id_contrato IS NOT NULL AND row.id_contrato <> '' THEN [row.id_contrato] ELSE [] END |
        MERGE (c:Contrato {id: cid})
        MERGE (c)-[:VINCULADO_A]->(pi)
    )
    """
    
    return load_csv_in_batches(filepath, query, batch_size=5000, desc="Proyectos BPIN", workers=1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_bpin()
