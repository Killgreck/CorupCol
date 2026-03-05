#!/usr/bin/env python3
"""
Watchdog — vigila los procesos de descarga y los reinicia si se caen.
Diseñado para correr toda la noche sin supervisión.
"""

import subprocess
import time
import json
import logging
import os
import signal
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/apolo/A/CorupCol")
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"
PIDS_DIR = LOGS_DIR / "pids"

PIDS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "watchdog.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

DATASETS = [
    "secop_integrado",
    "secop2_contratos",
    "secop2_procesos",
    "secop2_bpin",
    "sgr_ingresos",
    "sgr_giros",
    "chip_presupuesto",
    "cgr_funcionarios",
]

CHECK_INTERVAL = 60  # segundos entre chequeos


def is_done(name: str) -> bool:
    progress_file = BASE_DIR / "data" / name / "progress.json"
    if not progress_file.exists():
        return False
    try:
        d = json.loads(progress_file.read_text())
        return bool(d.get("done"))
    except Exception:
        return False


def get_progress(name: str) -> str:
    progress_file = BASE_DIR / "data" / name / "progress.json"
    if not progress_file.exists():
        return "sin datos aún"
    try:
        d = json.loads(progress_file.read_text())
        offset = d.get("offset", 0)
        total = d.get("total", 0)
        pct = 100 * offset / total if total else 0
        mb = d.get("total_mb", "?")
        if d.get("done"):
            return f"COMPLETO ✓ — {d.get('total_rows_descargadas', 0):,} filas | {mb} MB"
        return f"{offset:,}/{total:,} ({pct:.1f}%)"
    except Exception:
        return "error leyendo progreso"


def get_saved_pid(name: str):
    pidfile = PIDS_DIR / f"{name}.pid"
    if pidfile.exists():
        try:
            return int(pidfile.read_text().strip())
        except Exception:
            return None
    return None


def is_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def start_dataset(name: str):
    log_path = LOGS_DIR / f"{name}.log"
    pidfile = PIDS_DIR / f"{name}.pid"

    with open(log_path, "a") as logf:
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS_DIR / "download.py"), name],
            stdout=logf,
            stderr=logf,
            start_new_session=True,
        )

    pidfile.write_text(str(proc.pid))
    log.info(f"  → {name} lanzado con PID={proc.pid}")
    return proc.pid


def get_last_log_line(name: str) -> str:
    log_path = LOGS_DIR / f"{name}.log"
    if not log_path.exists():
        return ""
    try:
        result = subprocess.run(
            ["tail", "-1", str(log_path)],
            capture_output=True, text=True, timeout=5
        )
        line = result.stdout.strip()
        # Extraer solo la parte útil del log
        if "] " in line:
            line = line.split("] ", 2)[-1]
        return line
    except Exception:
        return ""


def main():
    log.info("=" * 55)
    log.info("WATCHDOG INICIADO — modo nocturno")
    log.info(f"Datasets: {', '.join(DATASETS)}")
    log.info("=" * 55)

    cycle = 0

    while True:
        cycle += 1
        log.info(f"--- Ciclo #{cycle} ({datetime.now().strftime('%H:%M:%S')}) ---")
        all_done = True

        for name in DATASETS:
            if is_done(name):
                log.info(f"  {name}: {get_progress(name)}")
                continue

            all_done = False
            pid = get_saved_pid(name)

            if is_alive(pid):
                last = get_last_log_line(name)
                progress = get_progress(name)
                log.info(f"  {name} [PID={pid}]: {progress} | {last}")
            else:
                log.warning(f"  {name}: CAÍDO (último PID={pid}). Reiniciando...")
                time.sleep(5)
                new_pid = start_dataset(name)
                time.sleep(3)
                if is_alive(new_pid):
                    log.info(f"  {name}: reiniciado OK (PID={new_pid})")
                else:
                    log.error(f"  {name}: falló al reiniciar — revisar log")

        if all_done:
            log.info("=" * 55)
            log.info("TODOS LOS DATASETS DESCARGADOS. Watchdog terminando.")
            log.info("=" * 55)
            break

        log.info(f"  Próximo chequeo en {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
