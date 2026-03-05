#!/usr/bin/env python3
"""
Descargador masivo de datos públicos colombianos.
Usa la API Socrata de datos.gov.co con paginación.
"""

import requests
import csv
import gzip
import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = BASE_DIR / "descarga.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

DATASETS = {
    "secop_integrado": {
        "id": "rpmr-utcd",
        "desc": "SECOP Integrado — contratos pre-2015 y legacy",
        "total_est": 21_431_663,
    },
    "secop2_contratos": {
        "id": "jbjy-vk9h",
        "desc": "SECOP II — Contratos Electrónicos",
        "total_est": 5_738_449,
    },
    "secop2_procesos": {
        "id": "p6dx-8zbt",
        "desc": "SECOP II — Procesos de Contratación",
        "total_est": 9_134_532,
    },
}

# Datasets adicionales verificados
DATASETS_EXTRA = {
    "secop2_bpin": {
        "id": "d9na-abhe",
        "desc": "SECOP II — BPIN por Proceso (vinculación contrato ↔ proyecto inversión)",
        "total_est": 2_416_135,
    },
    "sgr_ingresos": {
        "id": "rr3v-r3jc",
        "desc": "SGR — Presupuesto de Ingresos de Regalías Histórico",
        "total_est": 100_000,
    },
    "sgr_giros": {
        "id": "v9em-etch",
        "desc": "SGR — Giros por Departamento",
        "total_est": 10_370,
    },
    "chip_presupuesto": {
        "id": "nudc-7mev",
        "desc": "CHIP — Presupuesto Territorial (alcaldías y gobernaciones)",
        "total_est": 15_707,
    },
    "cgr_funcionarios": {
        "id": "7pn8-vpxh",
        "desc": "Directorio Funcionarios Contraloría General de la República",
        "total_est": 6_636,
    },
}

BASE_URL = "https://www.datos.gov.co/resource"
PAGE_SIZE = 50_000
DELAY = 0.5  # segundos entre peticiones


def get_total_rows(dataset_id: str) -> int:
    url = f"{BASE_URL}/{dataset_id}.json"
    r = requests.get(url, params={"$select": "count(*)"}, timeout=30)
    r.raise_for_status()
    return int(r.json()[0]["count"])


def get_progress_file(output_dir: Path) -> Path:
    return output_dir / "progress.json"


def load_progress(output_dir: Path) -> dict:
    pf = get_progress_file(output_dir)
    if pf.exists():
        return json.loads(pf.read_text())
    return {"offset": 0, "chunks": [], "total": 0, "done": False}


def save_progress(output_dir: Path, progress: dict):
    pf = get_progress_file(output_dir)
    pf.write_text(json.dumps(progress, indent=2))


def download_dataset(name: str, meta: dict):
    dataset_id = meta["id"]
    output_dir = DATA_DIR / name
    output_dir.mkdir(parents=True, exist_ok=True)

    progress = load_progress(output_dir)

    if progress.get("done"):
        log.info(f"[{name}] Ya descargado. Skipping.")
        return

    # Obtener total real
    if not progress["total"]:
        log.info(f"[{name}] Consultando total de filas...")
        try:
            progress["total"] = get_total_rows(dataset_id)
        except Exception as e:
            progress["total"] = meta.get("total_est", 0)
            log.warning(f"[{name}] No se pudo obtener total: {e}, usando estimado")
        save_progress(output_dir, progress)

    total = progress["total"]
    offset = progress["offset"]
    log.info(f"[{name}] {meta['desc']}")
    log.info(f"[{name}] Total: {total:,} filas | Iniciando en offset: {offset:,}")

    url = f"{BASE_URL}/{dataset_id}.csv"

    while offset < total:
        chunk_num = offset // PAGE_SIZE
        chunk_file = output_dir / f"chunk_{chunk_num:06d}.csv.gz"

        if chunk_file.exists():
            log.info(f"[{name}] Chunk {chunk_num} ya existe, saltando...")
            offset += PAGE_SIZE
            progress["offset"] = offset
            save_progress(output_dir, progress)
            continue

        params = {
            "$limit": PAGE_SIZE,
            "$offset": offset,
            "$order": ":id",
        }

        retry = 0
        max_retries = 5
        while retry < max_retries:
            try:
                log.info(f"[{name}] Descargando offset {offset:,}/{total:,} ({100*offset/total:.1f}%)")
                r = requests.get(url, params=params, timeout=180, stream=False)
                r.raise_for_status()

                content = r.text
                if not content.strip():
                    log.warning(f"[{name}] Respuesta vacía en offset {offset}, terminando")
                    offset = total  # forzar salida del while exterior
                    break

                lines = content.strip().split("\n")
                rows_in_chunk = len(lines) - 1  # -1 por el header

                # Eliminar archivo parcial si existía
                if chunk_file.exists():
                    chunk_file.unlink()

                with gzip.open(chunk_file, "wt", encoding="utf-8") as f:
                    f.write(content)

                size_mb = chunk_file.stat().st_size / 1024 / 1024
                log.info(f"[{name}] Chunk {chunk_num} guardado: {rows_in_chunk:,} filas | {size_mb:.1f} MB")

                progress["offset"] = offset + PAGE_SIZE
                progress["chunks"].append({
                    "chunk": chunk_num,
                    "offset": offset,
                    "rows": rows_in_chunk,
                    "file": str(chunk_file.name),
                    "size_mb": round(size_mb, 2),
                })
                save_progress(output_dir, progress)

                if rows_in_chunk < PAGE_SIZE:
                    log.info(f"[{name}] Último chunk detectado ({rows_in_chunk} < {PAGE_SIZE}). Descarga completa.")
                    offset = total  # forzar salida del while exterior
                break  # éxito — salir del retry loop

            except (requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.ConnectionError) as e:
                retry += 1
                wait = min(30 * retry, 120)
                log.warning(f"[{name}] Error de red ({type(e).__name__}) en offset {offset}. Intento {retry}/{max_retries}. Esperando {wait}s...")
                if chunk_file.exists():
                    chunk_file.unlink()
                time.sleep(wait)
            except requests.exceptions.HTTPError as e:
                retry += 1
                wait = 60
                log.error(f"[{name}] HTTP Error {e}. Intento {retry}/{max_retries}. Esperando {wait}s...")
                time.sleep(wait)
            except Exception as e:
                retry += 1
                wait = 30
                log.error(f"[{name}] Error inesperado ({type(e).__name__}: {e}). Intento {retry}/{max_retries}. Esperando {wait}s...")
                if chunk_file.exists():
                    chunk_file.unlink()
                time.sleep(wait)

        if retry == max_retries:
            log.error(f"[{name}] Máximo de reintentos alcanzado en offset {offset}. Abortando dataset.")
            save_progress(output_dir, progress)
            return

        offset += PAGE_SIZE
        time.sleep(DELAY)

    # Calcular stats finales
    total_rows = sum(c["rows"] for c in progress["chunks"])
    total_mb = sum(c["size_mb"] for c in progress["chunks"])
    progress["done"] = True
    progress["finished_at"] = datetime.now().isoformat()
    progress["total_rows_descargadas"] = total_rows
    progress["total_mb"] = round(total_mb, 2)
    save_progress(output_dir, progress)

    log.info(f"[{name}] COMPLETADO: {total_rows:,} filas | {total_mb:.1f} MB comprimido")


def print_summary():
    log.info("=" * 60)
    log.info("RESUMEN DE DESCARGA")
    log.info("=" * 60)
    for name in list(DATASETS.keys()) + list(DATASETS_EXTRA.keys()):
        output_dir = DATA_DIR / name
        pf = get_progress_file(output_dir)
        if pf.exists():
            p = json.loads(pf.read_text())
            status = "COMPLETO" if p.get("done") else f"EN PROGRESO ({p['offset']:,}/{p['total']:,})"
            mb = p.get("total_mb", "?")
            rows = p.get("total_rows_descargadas", p.get("offset", 0))
            log.info(f"  {name}: {status} | {rows:,} filas | {mb} MB")


def main():
    log.info("=" * 60)
    log.info("DESCARGA MASIVA — DATOS COLOMBIA ANTICORRUPCIÓN")
    log.info(f"Inicio: {datetime.now().isoformat()}")
    log.info("=" * 60)

    all_datasets = {**DATASETS, **DATASETS_EXTRA}

    target = sys.argv[1] if len(sys.argv) > 1 else None

    for name, meta in all_datasets.items():
        if target and name != target:
            continue
        try:
            download_dataset(name, meta)
        except KeyboardInterrupt:
            log.info("Descarga interrumpida por usuario. El progreso está guardado.")
            print_summary()
            sys.exit(0)
        except Exception as e:
            log.error(f"Error en {name}: {e}")
            continue

    print_summary()
    log.info("Descarga masiva finalizada.")


if __name__ == "__main__":
    main()
