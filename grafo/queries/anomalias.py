import logging
from grafo.config import db

logger = logging.getLogger(__name__)

QUERIES = {
    "empresa_reciente_contrato_millonario": """
    MATCH (c:Contratista)-[g:GANÓ]->(ct:Contrato)
    WITH c, MIN(ct.fecha_firma) AS primer_contrato, SUM(ct.valor) AS total_ganado, COUNT(ct) AS num_contratos
    WHERE total_ganado > 50000000 AND num_contratos >= 1
    RETURN c.doc_id, c.nombre, primer_contrato, total_ganado, num_contratos
    ORDER BY total_ganado DESC LIMIT 100
    """,

    "carrusel_contratista_multiples_entidades": """
    MATCH (c:Contratista)-[:GANÓ]->(ct:Contrato)<-[:FIRMÓ]-(e:Entidad)
    WITH c, COUNT(DISTINCT e) AS entidades_distintas, COUNT(ct) AS total_contratos, SUM(ct.valor) AS total_valor
    WHERE entidades_distintas >= 5 AND total_valor > 500000000
    RETURN c.doc_id, c.nombre, entidades_distintas, total_contratos, total_valor
    ORDER BY total_valor DESC LIMIT 100
    """,

    "licitaciones_unico_oferente": """
    MATCH (e:Entidad)-[:PUBLICÓ]->(p:Proceso {unico_oferente: true})-[:RESULTADO_DE*0..1]-(ct:Contrato)
    WITH e, COUNT(p) AS procesos_unico_oferente, SUM(ct.valor) AS valor_total
    WHERE procesos_unico_oferente >= 3
    RETURN e.nit, e.nombre, e.departamento, procesos_unico_oferente, valor_total
    ORDER BY valor_total DESC LIMIT 100
    """,

    "nepotismo_ordenador_recurrente": """
    MATCH (p:Persona)-[:ORDENÓ]->(ct:Contrato)<-[:GANÓ]-(c:Contratista)
    WITH p, c, COUNT(ct) AS contratos_juntos, SUM(ct.valor) AS valor_total
    WHERE contratos_juntos >= 3 AND valor_total > 100000000
    RETURN p.doc_id, p.nombre, c.doc_id, c.nombre AS contratista_nombre, contratos_juntos, valor_total
    ORDER BY contratos_juntos DESC LIMIT 100
    """,

    "autocontratacion_directa": """
    MATCH (p:Persona)-[:ORDENÓ]->(ct:Contrato)<-[:GANÓ]-(c:Contratista)<-[:ES_REP_LEGAL_DE]-(p2:Persona)
    WHERE p.doc_id = p2.doc_id
    RETURN p.doc_id, p.nombre, c.nombre AS contratista_nombre, ct.id, ct.valor, ct.fecha_firma
    ORDER BY ct.valor DESC LIMIT 200
    """,

    "sobrecosto_prorrogado": """
    MATCH (ct:Contrato)
    WHERE ct.dias_adicionados > 180 AND ct.valor > 100000000
    MATCH (e:Entidad)-[:FIRMÓ]->(ct)<-[:GANÓ]-(c:Contratista)
    RETURN e.nombre AS entidad_nombre, c.nombre AS contratista_nombre, ct.id, ct.valor, ct.dias_adicionados, ct.objeto
    ORDER BY ct.dias_adicionados DESC LIMIT 100
    """
}

def run_anomaly_queries():
    results = {}
    driver = db.get_driver()
    with driver.session() as session:
        for key, query in QUERIES.items():
            logger.info(f"Ejecutando query de anomalía: {key}")
            try:
                res = session.run(query)
                # Convert the records to a list of dicts directly
                # Ensure date/datetime types are converted to strings if needed for JSON serialization
                records = []
                for record in res:
                    row_dict = dict(record)
                    # Simple date conversion for JSON
                    for k, v in row_dict.items():
                        if hasattr(v, 'isoformat'):
                            row_dict[k] = v.isoformat()
                    records.append(row_dict)
                results[key] = records
            except Exception as e:
                logger.error(f"Error running {key}: {e}")
                results[key] = []
    return results
