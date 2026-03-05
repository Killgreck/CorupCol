#!/usr/bin/env python3
"""
Normalizador paralelo — usa multiprocessing.Pool para saturar todos los cores.
Cada chunk se procesa en un worker independiente.
"""

import gzip
import csv
import re
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, cpu_count, Manager
from functools import partial

BASE_DIR = Path("/home/apolo/A/CorupCol")
DATA_DIR = BASE_DIR / "data"
OUT_DIR  = BASE_DIR / "normalized"
OUT_DIR.mkdir(exist_ok=True)

WORKERS = cpu_count()  # 8 en tu i7

# ── Limpieza (pura, sin estado — segura para multiprocessing) ─────────────────

NULL_SET = {
    "", "no definido", "no aplica", "no aplica/no pertenece",
    "no adjudicado", "no definido.", "sin información", "ninguno",
    "n/a", "na", "nd", "-", "--", "no d", "no def",
}

def null(v):
    v = v.strip() if v else ""
    return None if v.lower() in NULL_SET else v

def clean_nit(raw):
    if not raw: return None
    digits = re.sub(r"[^\d]", "", raw.strip())
    if len(digits) > 10: digits = digits[:10]
    return digits if digits else None

def clean_name(raw):
    if not raw: return None
    v = null(raw)
    return " ".join(v.title().split()) if v else None

def parse_date(raw):
    if not raw: return None
    v = null(raw)
    if not v: return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
    return m.group(1) if m else None

def parse_value(raw):
    if not raw: return None
    v = null(raw)
    if not v: return None
    try: return float(re.sub(r"[^\d.]", "", v))
    except ValueError: return None

def year_of(d):
    return int(d[:4]) if d and len(d) >= 4 else None


# ── Workers (se ejecutan en procesos separados) ───────────────────────────────

def process_secop_integrado_chunk(chunk_path):
    """Procesa un chunk de SECOP Integrado. Retorna (rows, entidades, contratistas)."""
    rows = []
    entidades = {}
    contratistas = {}

    with gzip.open(chunk_path, "rt", encoding="utf-8", errors="replace") as f:
        for raw in csv.DictReader(f):
            nit_e  = clean_nit(raw.get("nit_de_la_entidad", ""))
            nom_e  = clean_name(raw.get("nombre_de_la_entidad", ""))
            doc_c  = clean_nit(raw.get("documento_proveedor", ""))
            nom_c  = clean_name(raw.get("nom_raz_social_contratista", ""))
            valor  = parse_value(raw.get("valor_contrato", ""))
            f_firma = parse_date(raw.get("fecha_de_firma_del_contrato", ""))
            f_ini  = parse_date(raw.get("fecha_inicio_ejecuci_n", ""))
            f_fin  = parse_date(raw.get("fecha_fin_ejecuci_n", ""))
            num_c  = null(raw.get("numero_del_contrato", ""))
            depto  = null(raw.get("departamento_entidad", ""))
            mpio   = null(raw.get("municipio_entidad", ""))
            modal  = null(raw.get("modalidad_de_contrataci_n", ""))
            tipo   = null(raw.get("tipo_de_contrato", ""))
            estado = null(raw.get("estado_del_proceso", ""))
            objeto = null(raw.get("objeto_a_contratar", "") or raw.get("objeto_del_proceso", ""))
            tipo_doc = null(raw.get("tipo_documento_proveedor", ""))

            if nit_e and nit_e not in entidades:
                entidades[nit_e] = {"nit": nit_e, "nombre": nom_e,
                                    "departamento": depto, "ciudad": mpio,
                                    "sector": None, "orden": None}
            if doc_c and doc_c not in contratistas:
                contratistas[doc_c] = {"doc_id": doc_c, "tipo_doc": tipo_doc,
                                       "nombre": nom_c, "rep_legal": None,
                                       "id_rep_legal": None, "es_pyme": None,
                                       "nacionalidad": None}
            if not num_c and not nit_e:
                continue

            rows.append({
                "numero_contrato": num_c,
                "nit_entidad":     nit_e,
                "doc_contratista": doc_c,
                "valor":           valor,
                "estado":          estado,
                "modalidad":       modal,
                "tipo":            tipo,
                "objeto":          objeto[:300] if objeto else None,
                "fecha_firma":     f_firma,
                "fecha_inicio":    f_ini,
                "fecha_fin":       f_fin,
                "anio":            year_of(f_firma or f_ini),
                "departamento":    depto,
                "municipio":       mpio,
                "origen":          "SECOP_I",
            })

    return rows, entidades, contratistas


def process_secop2_contratos_chunk(chunk_path):
    rows = []
    entidades = {}
    contratistas = {}

    with gzip.open(chunk_path, "rt", encoding="utf-8", errors="replace") as f:
        for raw in csv.DictReader(f):
            nit_e   = clean_nit(raw.get("nit_entidad", ""))
            nom_e   = clean_name(raw.get("nombre_entidad", ""))
            doc_c   = clean_nit(raw.get("documento_proveedor", ""))
            nom_c   = clean_name(raw.get("proveedor_adjudicado", ""))
            rep_l   = clean_name(raw.get("nombre_representante_legal", ""))
            id_rep  = clean_nit(raw.get("identificaci_n_representante_legal", ""))
            valor   = parse_value(raw.get("valor_del_contrato", ""))
            pagado  = parse_value(raw.get("valor_pagado", ""))
            pend    = parse_value(raw.get("valor_pendiente_de_ejecucion", ""))
            f_firma = parse_date(raw.get("fecha_de_firma", ""))
            f_ini   = parse_date(raw.get("fecha_de_inicio_del_contrato", ""))
            f_fin   = parse_date(raw.get("fecha_de_fin_del_contrato", ""))
            es_pyme = null(raw.get("es_pyme", ""))
            modal   = null(raw.get("modalidad_de_contratacion", ""))
            tipo    = null(raw.get("tipo_de_contrato", ""))
            estado  = null(raw.get("estado_contrato", ""))
            objeto  = null(raw.get("objeto_del_contrato", "") or raw.get("descripcion_del_proceso", ""))
            sector  = null(raw.get("sector", ""))
            orden_e = null(raw.get("orden", ""))
            depto   = null(raw.get("departamento", ""))
            ciudad  = null(raw.get("ciudad", ""))
            fuente  = ("SGR" if parse_value(raw.get("sistema_general_de_regal_as",""))
                       else "PGN" if parse_value(raw.get("presupuesto_general_de_la_nacion_pgn",""))
                       else "PROPIO")
            ordenador    = clean_name(raw.get("nombre_ordenador_del_gasto", ""))
            doc_ordenador = clean_nit(raw.get("n_mero_de_documento_ordenador_del_gasto", ""))
            dias_add = parse_value(raw.get("dias_adicionados", ""))
            id_c    = null(raw.get("id_contrato", ""))
            tipo_doc = null(raw.get("tipodocproveedor", ""))

            if nit_e and nit_e not in entidades:
                entidades[nit_e] = {"nit": nit_e, "nombre": nom_e,
                                    "departamento": depto, "ciudad": ciudad,
                                    "sector": sector, "orden": orden_e}
            if doc_c and doc_c not in contratistas:
                contratistas[doc_c] = {"doc_id": doc_c, "tipo_doc": tipo_doc,
                                       "nombre": nom_c, "rep_legal": rep_l,
                                       "id_rep_legal": id_rep, "es_pyme": es_pyme,
                                       "nacionalidad": null(raw.get("nacionalidad_representante_legal",""))}
            if not id_c:
                continue

            rows.append({
                "id_contrato":    id_c,
                "nit_entidad":    nit_e,
                "doc_contratista":doc_c,
                "valor":          valor,
                "valor_pagado":   pagado,
                "valor_pendiente":pend,
                "estado":         estado,
                "modalidad":      modal,
                "tipo":           tipo,
                "objeto":         objeto[:300] if objeto else None,
                "fecha_firma":    f_firma,
                "fecha_inicio":   f_ini,
                "fecha_fin":      f_fin,
                "anio":           year_of(f_firma or f_ini),
                "fuente_recursos":fuente,
                "dias_adicionados":int(dias_add) if dias_add else 0,
                "ordenador_gasto":ordenador,
                "doc_ordenador":  doc_ordenador,
                "supervisor":     clean_name(raw.get("nombre_supervisor","")),
                "es_pyme":        es_pyme,
                "proceso_id":     null(raw.get("proceso_de_compra","")),
            })

    return rows, entidades, contratistas


def process_secop2_procesos_chunk(chunk_path):
    rows = []
    entidades = {}
    contratistas = {}

    with gzip.open(chunk_path, "rt", encoding="utf-8", errors="replace") as f:
        for raw in csv.DictReader(f):
            nit_e     = clean_nit(raw.get("nit_entidad", ""))
            nom_e     = clean_name(raw.get("entidad", ""))
            doc_prov  = clean_nit(raw.get("nit_del_proveedor_adjudicado", ""))
            nom_prov  = clean_name(raw.get("nombre_del_proveedor", ""))
            id_proc   = null(raw.get("id_del_proceso", ""))
            precio    = parse_value(raw.get("precio_base", ""))
            val_adj   = parse_value(raw.get("valor_total_adjudicacion", ""))
            modal     = null(raw.get("modalidad_de_contratacion", ""))
            estado    = null(raw.get("estado_resumen", ""))
            adj       = null(raw.get("adjudicado", ""))
            f_pub     = parse_date(raw.get("fecha_de_publicacion_del", ""))
            f_adj     = parse_date(raw.get("fecha_adjudicacion", ""))
            inv       = parse_value(raw.get("proveedores_invitados", ""))
            resp      = parse_value(raw.get("respuestas_al_procedimiento", ""))
            tipo      = null(raw.get("tipo_de_contrato", ""))
            desc      = null(raw.get("descripci_n_del_procedimiento", ""))
            depto     = null(raw.get("departamento_entidad", ""))
            adjudicador = clean_name(raw.get("nombre_del_adjudicador", ""))
            unico     = (resp is not None and resp <= 1 and val_adj is not None and val_adj > 0)

            if nit_e and nit_e not in entidades:
                entidades[nit_e] = {"nit": nit_e, "nombre": nom_e,
                                    "departamento": depto, "ciudad": None,
                                    "sector": None, "orden": null(raw.get("ordenentidad",""))}
            if doc_prov and doc_prov not in contratistas:
                contratistas[doc_prov] = {"doc_id": doc_prov, "tipo_doc": "NIT",
                                          "nombre": nom_prov, "rep_legal": None,
                                          "id_rep_legal": None, "es_pyme": None,
                                          "nacionalidad": None}
            if not id_proc:
                continue

            rows.append({
                "id_proceso":         id_proc,
                "nit_entidad":        nit_e,
                "doc_adjudicado":     doc_prov,
                "precio_base":        precio,
                "valor_adjudicado":   val_adj,
                "modalidad":          modal,
                "tipo_contrato":      tipo,
                "estado":             estado,
                "adjudicado":         adj,
                "fecha_publicacion":  f_pub,
                "fecha_adjudicacion": f_adj,
                "anio":               year_of(f_pub),
                "proveedores_invitados": int(inv) if inv else 0,
                "respuestas":         int(resp) if resp else 0,
                "unico_oferente":     unico,
                "adjudicador":        adjudicador,
                "descripcion":        desc[:300] if desc else None,
                "depto_entidad":      depto,
            })

    return rows, entidades, contratistas


# ── Wrapper de worker: escribe filas a archivo temp, solo devuelve (n, ents, conts) ──

def _worker(args):
    """Wrapper que ejecuta worker_fn y escribe filas al disco localmente.
    Solo devuelve (n_rows, ents, conts) por IPC — sin filas."""
    chunk_path, worker_fn, temp_dir = args
    try:
        rows, ents, conts = worker_fn(chunk_path)
    except Exception as exc:
        return 0, {}, {}, str(exc)

    if rows:
        temp_file = Path(temp_dir) / (chunk_path.stem + ".csv")
        with open(temp_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    return len(rows), ents, conts, None


# ── Orquestador paralelo ──────────────────────────────────────────────────────

def run_parallel(dataset_name, worker_fn, out_filename, skip_if_exists=True):
    out_path = OUT_DIR / out_filename
    chunks = sorted((DATA_DIR / dataset_name).glob("chunk_*.csv.gz"))

    if skip_if_exists and out_path.exists():
        print(f"[{dataset_name}] {out_filename} ya existe — skipping (entidades se reconstruyen al final)")
        return {}, {}

    temp_dir = OUT_DIR / f"_tmp_{dataset_name}"
    temp_dir.mkdir(exist_ok=True)

    print(f"[{dataset_name}] Procesando {len(chunks)} chunks con {WORKERS} workers...")
    t0 = time.time()

    all_ents  = {}
    all_conts = {}
    done      = 0
    total_rows = 0
    errors    = 0

    args = [(c, worker_fn, temp_dir) for c in chunks]

    with Pool(processes=WORKERS) as pool:
        for n_rows, ents, conts, err in pool.imap_unordered(_worker, args, chunksize=1):
            if err:
                errors += 1
                print(f"  [ERROR] {err}", flush=True)
                continue
            all_ents.update(ents)
            all_conts.update(conts)
            total_rows += n_rows
            done += 1

            if done % 20 == 0 or done == len(chunks):
                elapsed = time.time() - t0
                rate = done / elapsed
                eta = (len(chunks) - done) / rate if rate > 0 else 0
                print(f"  {done}/{len(chunks)} chunks | {total_rows:,} filas | "
                      f"{elapsed:.0f}s | ETA: {eta:.0f}s", flush=True)

    # Concatenar archivos temporales en el CSV final
    print(f"  Concatenando {done} archivos temporales → {out_filename}...", flush=True)
    temp_files = sorted(temp_dir.glob("*.csv"))
    header_written = False
    final_rows = 0
    with open(out_path, "w", newline="", encoding="utf-8") as fout:
        for tf in temp_files:
            with open(tf, "r", encoding="utf-8") as fin:
                first_line = fin.readline()          # cabecera
                if not header_written:
                    fout.write(first_line)
                    header_written = True
                for line in fin:
                    fout.write(line)
                    final_rows += 1

    # Limpiar temporales
    for tf in temp_files:
        tf.unlink()
    temp_dir.rmdir()

    elapsed = time.time() - t0
    size_gb = out_path.stat().st_size / 1e9
    print(f"  → {out_filename}: {final_rows:,} filas | {size_gb:.2f} GB | {elapsed:.0f}s"
          + (f" | {errors} errores" if errors else ""), flush=True)

    return all_ents, all_conts


def rebuild_nodes_from_csvs():
    """Reconstruye entidades/contratistas desde los CSVs ya generados."""
    all_ents  = {}
    all_conts = {}
    for fname, nit_col, doc_col in [
        ("contratos_s2.csv",   "nit_entidad", "doc_contratista"),
        ("procesos_s2.csv",    "nit_entidad", "doc_adjudicado"),
        ("contratos_legacy.csv", "nit_entidad", "doc_contratista"),
    ]:
        fpath = OUT_DIR / fname
        if not fpath.exists():
            continue
        print(f"  Escaneando {fname} para entidades/contratistas...", flush=True)
        with open(fpath, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nit = row.get(nit_col)
                doc = row.get(doc_col)
                if nit and nit not in all_ents:
                    all_ents[nit] = {"nit": nit,
                                     "nombre": row.get("nombre_entidad") or row.get("adjudicador") or None,
                                     "departamento": row.get("departamento") or row.get("depto_entidad") or None,
                                     "ciudad": row.get("municipio") or None,
                                     "sector": row.get("sector") or None,
                                     "orden": row.get("orden") or None}
                if doc and doc not in all_conts:
                    all_conts[doc] = {"doc_id": doc, "tipo_doc": None, "nombre": None,
                                      "rep_legal": None, "id_rep_legal": None,
                                      "es_pyme": None, "nacionalidad": None}
    print(f"  → {len(all_ents):,} entidades | {len(all_conts):,} contratistas", flush=True)
    return all_ents, all_conts


def write_node_csvs(all_ents, all_conts):
    # Entidades
    ent_path = OUT_DIR / "entidades.csv"
    ents = list(all_ents.values())
    with open(ent_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["nit","nombre","departamento","ciudad","sector","orden"])
        w.writeheader()
        w.writerows(ents)
    print(f"  → entidades.csv: {len(ents):,} nodos únicos")

    # Contratistas
    cont_path = OUT_DIR / "contratistas.csv"
    conts = list(all_conts.values())
    with open(cont_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc_id","tipo_doc","nombre","rep_legal",
                                           "id_rep_legal","es_pyme","nacionalidad"])
        w.writeheader()
        w.writerows(conts)
    print(f"  → contratistas.csv: {len(conts):,} nodos únicos")


def normalize_bpin():
    out = OUT_DIR / "bpin.csv"
    if out.exists():
        print("[bpin] Ya existe — skipping")
        return
    rows = []
    for chunk in sorted((DATA_DIR / "secop2_bpin").glob("chunk_*.csv.gz")):
        with gzip.open(chunk, "rt", encoding="utf-8", errors="replace") as f:
            for raw in csv.DictReader(f):
                rows.append({
                    "id_proceso":    null(raw.get("id_proceso","")),
                    "id_contrato":   null(raw.get("id_contracto","")),
                    "codigo_bpin":   null(raw.get("codigo_bpin","")),
                    "anno_bpin":     null(raw.get("anno_bpin","")),
                    "id_portafolio": null(raw.get("id_portafolio","")),
                    "validacion":    null(raw.get("validacion_bpin","")),
                })
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  → bpin.csv: {len(rows):,} filas")


def normalize_sgr():
    for ds, fname in [("sgr_ingresos","sgr_ingresos.csv"), ("sgr_giros","sgr_giros.csv")]:
        out = OUT_DIR / fname
        if out.exists():
            print(f"[{ds}] Ya existe — skipping")
            continue
        rows = []
        for chunk in sorted((DATA_DIR / ds).glob("chunk_*.csv.gz")):
            with gzip.open(chunk, "rt", encoding="utf-8", errors="replace") as f:
                for raw in csv.DictReader(f):
                    rows.append({k: null(v) for k, v in raw.items()})
        if rows:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            print(f"  → {fname}: {len(rows):,} filas")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(f"NORMALIZADOR PARALELO — {WORKERS} workers (i7 {cpu_count()} threads)")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    # 1. SECOP II Contratos (skip si ya existe)
    run_parallel("secop2_contratos", process_secop2_contratos_chunk,
                 "contratos_s2.csv", skip_if_exists=True)

    # 2. SECOP II Procesos (skip si ya existe)
    run_parallel("secop2_procesos", process_secop2_procesos_chunk,
                 "procesos_s2.csv", skip_if_exists=True)

    # 3. SECOP Integrado legacy — EL GRANDE (429 chunks, 31M filas)
    run_parallel("secop_integrado", process_secop_integrado_chunk,
                 "contratos_legacy.csv", skip_if_exists=True)

    # 4. Reconstruir nodos deduplicados desde los CSVs generados
    print("\n=== Reconstruyendo nodos desde CSVs ===", flush=True)
    all_ents, all_conts = rebuild_nodes_from_csvs()
    write_node_csvs(all_ents, all_conts)

    # 5. Datasets pequeños
    print("\n=== Datasets auxiliares ===")
    normalize_bpin()
    normalize_sgr()

    print(f"\n✓ COMPLETADO: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Archivos en: {OUT_DIR}")
