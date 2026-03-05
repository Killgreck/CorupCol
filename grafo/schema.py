import logging
from grafo.config import db

logger = logging.getLogger(__name__)

# List of constraints and indexes exactly as required
SCHEMA_QUERIES = [
    "CREATE CONSTRAINT entidad_nit IF NOT EXISTS FOR (e:Entidad) REQUIRE e.nit IS UNIQUE;",
    "CREATE CONSTRAINT contratista_doc IF NOT EXISTS FOR (c:Contratista) REQUIRE c.doc_id IS UNIQUE;",
    "CREATE CONSTRAINT contrato_id IF NOT EXISTS FOR (c:Contrato) REQUIRE c.id IS UNIQUE;",
    "CREATE CONSTRAINT proceso_id IF NOT EXISTS FOR (p:Proceso) REQUIRE p.id IS UNIQUE;",
    "CREATE CONSTRAINT persona_doc IF NOT EXISTS FOR (p:Persona) REQUIRE p.doc_id IS UNIQUE;",
    "CREATE INDEX contrato_anio IF NOT EXISTS FOR (c:Contrato) ON (c.anio);",
    "CREATE INDEX contrato_valor IF NOT EXISTS FOR (c:Contrato) ON (c.valor);",
    "CREATE INDEX contrato_modalidad IF NOT EXISTS FOR (c:Contrato) ON (c.modalidad);",
    "CREATE INDEX proceso_unico_oferente IF NOT EXISTS FOR (p:Proceso) ON (p.unico_oferente);"
]

def setup_schema():
    """
    Executes the CYPHER queries needed for indexes and constraints before data loading.
    """
    logger.info("Creando constraints e índices...")
    driver = db.get_driver()
    with driver.session() as session:
        for query in SCHEMA_QUERIES:
            try:
                session.run(query)
            except Exception as e:
                logger.error(f"Error creating schema with query '{query}': {e}")
                raise
    logger.info("Constraints e índices creados/verificados correctamente.")
