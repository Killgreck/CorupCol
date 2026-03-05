import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Iterator, List, Dict, Any
from grafo.config import db

logger = logging.getLogger(__name__)

WORKERS = 6
BATCH_SIZE = 5000
MAX_RETRIES = 5

def iter_csv_batches(filepath: str, batch_size: int = BATCH_SIZE) -> Iterator[List[Dict[str, Any]]]:
    """Reads a CSV block by block using an iterator."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                batch.append(row)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return

def execute_batch(query: str, batch: List[Dict[str, Any]], db_conn=None, extra_params: dict = None):
    """Executes a Cypher UNWIND query, retrying on transient errors (deadlocks)."""
    conn = db_conn or db
    driver = conn.get_driver()
    params = {"batch": batch}
    if extra_params:
        params.update(extra_params)
    for attempt in range(MAX_RETRIES):
        try:
            with driver.session() as session:
                session.run(query, **params)
            return
        except Exception as e:
            if "TransientError" in str(e) and attempt < MAX_RETRIES - 1:
                wait_secs = 0.2 * (2 ** attempt)
                logger.debug(f"Deadlock detectado, reintento {attempt+1}/{MAX_RETRIES} en {wait_secs:.1f}s")
                time.sleep(wait_secs)
            else:
                raise

def load_csv_in_batches(filepath: str, query: str, batch_size: int = BATCH_SIZE,
                        desc: str = "Records", extra_params: dict = None, workers: int = WORKERS):
    """
    Reads CSV and executes batches in parallel using a sliding window of WORKERS
    in-flight futures. Avoids loading the entire file into memory at once.
    """
    total_processed = 0
    logger.info(f"Comenzando carga de {desc} desde {filepath}...")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {}  # future -> batch_size

        for batch in iter_csv_batches(filepath, batch_size):
            # Drain completed futures if we're at max capacity
            while len(pending) >= workers:
                done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                for f in done:
                    f.result()  # propagate exceptions
                    total_processed += pending.pop(f)
                    if total_processed % 50000 == 0:
                        logger.info(f"  [{desc}] {total_processed:,} registros cargados...")

            future = executor.submit(execute_batch, query, batch, None, extra_params)
            pending[future] = len(batch)

        # Wait for remaining in-flight batches
        for f in pending:
            f.result()
            total_processed += pending[f]

    logger.info(f"Carga finalizada para {desc}: {total_processed:,} registros procesados.")
    return total_processed
