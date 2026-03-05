"""
Extrae pares (doc_rep_legal, nit_contratista) desde los chunks crudos de SECOP II
y crea la relación (:Persona)-[:ES_REP_LEGAL_DE]->(:Contratista) en Neo4j.

Solo se ejecuta una vez — usa MERGE para ser idempotente.
"""
import gzip
import csv
import io
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("REP_LEGAL")

DATA_DIR  = Path("/home/apolo/A/CorupCol/data/secop2_contratos")
NEO4J_URI = "bolt://localhost:7687"
BATCH_SIZE = 3000
WORKERS    = 4
MAX_RETRIES = 5

driver = GraphDatabase.driver(NEO4J_URI, auth=("neo4j", ""))

QUERY = """
UNWIND $batch AS row
WITH row WHERE row.rep_doc IS NOT NULL AND row.nit IS NOT NULL

MERGE (p:Persona {doc_id: row.rep_doc})
ON CREATE SET p.nombre = row.rep_nombre, p.rol = 'rep_legal'
ON MATCH SET  p.nombre = CASE WHEN p.nombre IS NULL OR p.nombre = 'Desconocido'
                               THEN row.rep_nombre ELSE p.nombre END

MERGE (c:Contratista {doc_id: row.nit})

MERGE (p)-[:ES_REP_LEGAL_DE]->(c)
"""


def execute_batch(batch):
    for attempt in range(MAX_RETRIES):
        try:
            with driver.session() as session:
                session.run(QUERY, batch=batch)
            return len(batch)
        except Exception as e:
            if "TransientError" in str(e) and attempt < MAX_RETRIES - 1:
                time.sleep(0.2 * (2 ** attempt))
            else:
                raise


def extraer_pares_chunk(path: Path) -> list:
    """Extrae pares únicos (rep_doc, nit, rep_nombre) de un chunk gz."""
    vistos = set()
    pares = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nit      = row.get("documento_proveedor", "").strip()
            rep_doc  = row.get("identificaci_n_representante_legal", "").strip()
            rep_nom  = row.get("nombre_representante_legal", "").strip().title()

            if not nit or not rep_doc or len(rep_doc) < 5:
                continue
            # Descartar docs genéricos
            if rep_doc in {"0","123456","1234567","12345678","123456789",
                           "000000","0000000","00000000","000000000"}:
                continue
            key = (rep_doc, nit)
            if key not in vistos:
                vistos.add(key)
                pares.append({"rep_doc": rep_doc, "nit": nit, "rep_nombre": rep_nom or "Desconocido"})
    return pares


def main():
    chunks = sorted(DATA_DIR.glob("chunk_*.csv.gz"))
    log.info(f"Procesando {len(chunks)} chunks de SECOP II...")

    total_pares   = 0
    total_cargados = 0
    pending = {}

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        batch_acum = []

        for i, chunk in enumerate(chunks):
            pares = extraer_pares_chunk(chunk)
            total_pares += len(pares)
            batch_acum.extend(pares)

            # Enviar en batches
            while len(batch_acum) >= BATCH_SIZE:
                lote = batch_acum[:BATCH_SIZE]
                batch_acum = batch_acum[BATCH_SIZE:]

                while len(pending) >= WORKERS:
                    done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                    for f in done:
                        total_cargados += f.result()
                        del pending[f]

                future = executor.submit(execute_batch, lote)
                pending[future] = len(lote)

            if (i + 1) % 10 == 0:
                log.info(f"  {i+1}/{len(chunks)} chunks | pares únicos extraídos: {total_pares:,} | cargados: {total_cargados:,}")

        # Último batch residual
        if batch_acum:
            while len(pending) >= WORKERS:
                done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                for f in done:
                    total_cargados += f.result()
                    del pending[f]
            future = executor.submit(execute_batch, batch_acum)
            pending[future] = len(batch_acum)

        for f in pending:
            total_cargados += f.result()

    log.info(f"Completado. Pares únicos encontrados: {total_pares:,} | Relaciones cargadas: {total_cargados:,}")
    driver.close()


if __name__ == "__main__":
    main()
