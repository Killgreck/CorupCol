import logging
from grafo.config import db

logger = logging.getLogger(__name__)

def fetch_top_20(query_key: str):
    """Auxiliary to get top 20 requested purely for summary."""
    # Assuming the reports from anomaly queries also cover these limits but for stats:
    pass

def get_graph_stats():
    driver = db.get_driver()
    stats = {}
    with driver.session() as session:
        logger.info("Recopilando estadísticas globales del grafo...")
        try:
            # Nodos
            stats['total_nodos'] = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            # Relaciones
            stats['total_relaciones'] = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
            # Valor total contratos
            stats['valor_total_contratos'] = session.run("MATCH (c:Contrato) RETURN sum(c.valor) AS sum").single()["sum"]
            
            # Top 20 Contratistas
            top_contratistas = session.run("""
                MATCH (c:Contratista)-[:GANÓ]->(ct:Contrato)
                RETURN c.nombre AS contratista, SUM(ct.valor) AS total
                ORDER BY total DESC LIMIT 20
            """)
            stats['top_20_contratistas_acumulado'] = [dict(record) for record in top_contratistas]

            # Top 20 Entidades con más únicos oferentes
            top_entidades_unico = session.run("""
                MATCH (e:Entidad)-[:PUBLICÓ]->(p:Proceso {unico_oferente: true})
                RETURN e.nombre AS entidad, COUNT(p) AS procesos_unico
                ORDER BY procesos_unico DESC LIMIT 20
            """)
            stats['top_20_entidades_unico_oferente'] = [dict(record) for record in top_entidades_unico]

            # Top 20 pares (ordenador, contratista)
            top_ordenador_contratista = session.run("""
                MATCH (p:Persona)-[:ORDENÓ]->(ct:Contrato)<-[:GANÓ]-(c:Contratista)
                RETURN p.nombre AS ordenador, c.nombre AS contratista, COUNT(ct) AS recurrentes
                ORDER BY recurrentes DESC LIMIT 20
            """)
            stats['top_20_ordenador_contratista'] = [dict(record) for record in top_ordenador_contratista]
            
        except Exception as e:
            logger.error(f"Error recopilando estadísticas: {e}")
    
    return stats
