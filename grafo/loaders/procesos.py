import os
import logging
from grafo.config import DATA_DIR
from grafo.loaders.base_loader import load_csv_in_batches

logger = logging.getLogger(__name__)

def load_procesos():
    filepath = os.path.join(DATA_DIR, 'procesos_s2.csv')
    if not os.path.exists(filepath):
        logger.warning(f"Archivo {filepath} no existe, omitiendo carga de procesos.")
        return 0

    query = """
    UNWIND $batch AS row

    // Saltar filas sin ID de proceso
    WITH row WHERE row.id_proceso IS NOT NULL AND row.id_proceso <> ''

    MERGE (p:Proceso {id: row.id_proceso})
    ON CREATE SET
        p.precio_base          = toFloat(coalesce(row.precio_base, '0')),
        p.valor_adjudicado     = toFloat(coalesce(row.valor_adjudicado, '0')),
        p.modalidad            = row.modalidad,
        p.tipo_contrato        = row.tipo_contrato,
        p.estado               = row.estado,
        p.fecha_publicacion    = CASE WHEN row.fecha_publicacion IS NOT NULL AND row.fecha_publicacion <> '' THEN date(row.fecha_publicacion) ELSE null END,
        p.fecha_adjudicacion   = CASE WHEN row.fecha_adjudicacion IS NOT NULL AND row.fecha_adjudicacion <> '' THEN date(row.fecha_adjudicacion) ELSE null END,
        p.anio                 = toInteger(coalesce(row.anio, '0')),
        p.proveedores_invitados = toInteger(coalesce(row.proveedores_invitados, '0')),
        p.respuestas           = toInteger(coalesce(row.respuestas, '0')),
        p.unico_oferente       = (row.unico_oferente = 'True'),
        p.descripcion          = row.descripcion

    WITH p, row
    FOREACH (nit IN CASE WHEN row.nit_entidad IS NOT NULL AND row.nit_entidad <> '' THEN [row.nit_entidad] ELSE [] END |
        MERGE (e:Entidad {nit: nit})
        MERGE (e)-[:PUBLICÓ]->(p)
    )

    // Adjudicado: contratista ganador del proceso
    WITH p, row
    FOREACH (doc IN CASE WHEN row.doc_adjudicado IS NOT NULL AND row.doc_adjudicado <> '' THEN [row.doc_adjudicado] ELSE [] END |
        MERGE (c:Contratista {doc_id: doc})
        MERGE (c)-[:PARTICIPÓ_EN]->(p)
    )
    """
    
    return load_csv_in_batches(filepath, query, batch_size=1000, desc="Procesos SECOP II")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_procesos()
