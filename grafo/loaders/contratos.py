import os
import logging
from grafo.config import DATA_DIR
from grafo.loaders.base_loader import load_csv_in_batches

logger = logging.getLogger(__name__)

def load_contratos(filename: str, origen: str):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"Archivo {filepath} no existe, omitiendo origen {origen}")
        return 0

    # Columna de ID: SECOP II usa id_contrato, legacy usa numero_contrato
    query = """
    UNWIND $batch AS row

    // ID unificado: id_contrato (SECOP II) o numero_contrato (legacy)
    WITH row,
         coalesce(
             CASE WHEN row.id_contrato IS NOT NULL AND row.id_contrato <> '' THEN row.id_contrato END,
             CASE WHEN row.numero_contrato IS NOT NULL AND row.numero_contrato <> '' THEN row.numero_contrato END
         ) AS contract_id

    // Saltar filas sin ID
    WHERE contract_id IS NOT NULL

    MERGE (ct:Contrato {id: contract_id})
    ON CREATE SET
        ct.valor            = toFloat(coalesce(row.valor, '0')),
        ct.valor_pagado     = toFloat(coalesce(row.valor_pagado, '0')),
        ct.valor_pendiente  = toFloat(coalesce(row.valor_pendiente, '0')),
        ct.estado           = row.estado,
        ct.modalidad        = row.modalidad,
        ct.tipo             = row.tipo,
        ct.objeto           = row.objeto,
        ct.fecha_firma      = CASE WHEN row.fecha_firma IS NOT NULL AND row.fecha_firma <> '' THEN date(row.fecha_firma) ELSE null END,
        ct.fecha_inicio     = CASE WHEN row.fecha_inicio IS NOT NULL AND row.fecha_inicio <> '' THEN date(row.fecha_inicio) ELSE null END,
        ct.fecha_fin        = CASE WHEN row.fecha_fin IS NOT NULL AND row.fecha_fin <> '' THEN date(row.fecha_fin) ELSE null END,
        ct.anio             = toInteger(coalesce(row.anio, '0')),
        ct.fuente_recursos  = row.fuente_recursos,
        ct.dias_adicionados = toInteger(coalesce(row.dias_adicionados, '0')),
        ct.origen           = $origen

    // Entidad FIRMÓ Contrato
    WITH ct, row
    FOREACH (nit IN CASE WHEN row.nit_entidad IS NOT NULL AND row.nit_entidad <> '' THEN [row.nit_entidad] ELSE [] END |
        MERGE (e:Entidad {nit: nit})
        MERGE (e)-[f:FIRMÓ]->(ct)
        ON CREATE SET f.fecha = ct.fecha_firma
    )

    // Contratista GANÓ Contrato
    WITH ct, row
    FOREACH (doc IN CASE WHEN row.doc_contratista IS NOT NULL AND row.doc_contratista <> '' THEN [row.doc_contratista] ELSE [] END |
        MERGE (c:Contratista {doc_id: doc})
        MERGE (c)-[g:GANÓ]->(ct)
        ON CREATE SET g.valor = ct.valor, g.anio = ct.anio
    )

    // Proceso → Contrato (proceso_id en SECOP II)
    WITH ct, row
    FOREACH (pid IN CASE WHEN row.proceso_id IS NOT NULL AND row.proceso_id <> '' THEN [row.proceso_id] ELSE [] END |
        MERGE (p:Proceso {id: pid})
        MERGE (ct)-[:RESULTADO_DE]->(p)
    )

    // Ordenador del gasto: columna doc_ordenador (cédula/NIT) + ordenador_gasto (nombre)
    WITH ct, row
    FOREACH (doc_ord IN CASE WHEN row.doc_ordenador IS NOT NULL AND row.doc_ordenador <> '' THEN [row.doc_ordenador] ELSE [] END |
        MERGE (p_ord:Persona {doc_id: doc_ord})
        ON CREATE SET p_ord.nombre = coalesce(row.ordenador_gasto, 'Desconocido'),
                      p_ord.rol    = 'ordenador_gasto'
        MERGE (p_ord)-[:ORDENÓ {cargo: 'Ordenador del Gasto'}]->(ct)
    )
    """

    # Legacy usa workers=1 para evitar deadlocks (nodos compartidos entre batches)
    w = 1 if origen == 'SECOP_I' else 6
    return load_csv_in_batches(filepath, query, batch_size=5000,
                               desc=f"Contratos {origen}", extra_params={"origen": origen},
                               workers=w)

def load_all_contratos():
    total_legacy = load_contratos('contratos_legacy.csv', origen='SECOP_I')
    total_s2 = load_contratos('contratos_s2.csv', origen='SECOP_II')
    return total_legacy + total_s2

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_all_contratos()
