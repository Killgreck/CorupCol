#!/usr/bin/env python3
"""
Normalizador de datos SECOP para construcción de grafo Neo4j.
Produce CSVs limpios y deduplicados listos para importar.

Salida en: /home/apolo/A/CorupCol/normalized/
  - entidades.csv        → nodos Entidad (gobierno)
  - contratistas.csv     → nodos Contratista (empresas/personas)
  - contratos.csv        → nodos Contrato + relaciones
  - procesos.csv         → nodos Proceso (licitaciones)
  - bpin.csv             → relaciones Contrato ↔ ProyectoInversion
  - sgr.csv              → nodos SGR (regalías)
"""

import gzip
import csv
import json
import re
import logging
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path("/home/apolo/A/CorupCol")
DATA_DIR = BASE_DIR / "data"
OUT_DIR  = BASE_DIR / "normalized"
OUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "normalize.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Constantes de limpieza ─────────────────────────────────────────────────────

NULL_VALUES = {
    "", "no definido", "no aplica", "no aplica/no pertenece",
    "no adjudicado", "no definido.", "sin información", "ninguno",
    "n/a", "na", "nd", "-", "--", "no d", "no def",
}

def null(v: str):
    """Retorna None si el valor es vacío/nulo, si no retorna el valor limpio."""
    v = v.strip() if v else ""
    return None if v.lower() in NULL_VALUES else v


def clean_nit(raw: str) -> str | None:
    """Elimina puntos, comas, guiones y dígitos de verificación. Retorna solo dígitos."""
    if not raw:
        return None
    # Quitar todo excepto dígitos (los puntos, guiones y dígito verificación)
    digits = re.sub(r"[^\d]", "", raw.strip())
    # Si tiene más de 10 dígitos probablemente tiene dígito de verificación al final
    if len(digits) > 10:
        digits = digits[:10]
    return digits if digits else None


def clean_name(raw: str) -> str | None:
    """Title Case, colapsa espacios múltiples."""
    if not raw:
        return None
    v = null(raw)
    if not v:
        return None
    return " ".join(v.title().split())


def parse_date(raw: str) -> str | None:
    """Extrae YYYY-MM-DD de fechas ISO o variantes."""
    if not raw:
        return None
    v = null(raw)
    if not v:
        return None
    # Formato: 2020-02-13T00:00:00.000
    m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
    return m.group(1) if m else None


def parse_value(raw: str) -> float | None:
    """Convierte string a float, retorna None si inválido."""
    if not raw:
        return None
    v = null(raw)
    if not v:
        return None
    try:
        return float(re.sub(r"[^\d.]", "", v))
    except ValueError:
        return None


def year_of(date_str: str | None) -> int | None:
    if date_str and len(date_str) >= 4:
        try:
            return int(date_str[:4])
        except Exception:
            return None
    return None


def iter_chunks(dataset: str):
    """Itera sobre todos los chunks de un dataset."""
    folder = DATA_DIR / dataset
    chunks = sorted(folder.glob("chunk_*.csv.gz"))
    log.info(f"  {dataset}: {len(chunks)} chunks")
    for chunk in chunks:
        with gzip.open(chunk, "rt", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            yield from reader


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log.info(f"  → {path.name}: {len(rows):,} registros")


# ── Colecciones globales para deduplicación ───────────────────────────────────

entidades   = {}   # nit → dict
contratistas = {}  # doc_id → dict


def upsert_entidad(nit, nombre, departamento=None, ciudad=None, sector=None, orden=None):
    if not nit:
        return
    if nit not in entidades:
        entidades[nit] = {
            "nit": nit,
            "nombre": nombre,
            "departamento": departamento,
            "ciudad": ciudad,
            "sector": sector,
            "orden": orden,
        }
    else:
        # Actualizar campos vacíos
        e = entidades[nit]
        if nombre and not e["nombre"]:
            e["nombre"] = nombre
        if departamento and not e["departamento"]:
            e["departamento"] = departamento


def upsert_contratista(doc_id, tipo_doc, nombre, rep_legal=None, id_rep=None,
                        es_pyme=None, nacionalidad=None):
    if not doc_id:
        return
    if doc_id not in contratistas:
        contratistas[doc_id] = {
            "doc_id": doc_id,
            "tipo_doc": tipo_doc,
            "nombre": nombre,
            "rep_legal": rep_legal,
            "id_rep_legal": id_rep,
            "es_pyme": es_pyme,
            "nacionalidad": nacionalidad,
        }
    else:
        c = contratistas[doc_id]
        if nombre and not c["nombre"]:
            c["nombre"] = nombre
        if rep_legal and not c["rep_legal"]:
            c["rep_legal"] = rep_legal
            c["id_rep_legal"] = id_rep


# ── 1. SECOP II — Contratos ────────────────────────────────────────────────────

def repopulate_from_existing(csv_path: Path, nit_col: str, nombre_col: str,
                              depto_col: str, doc_col: str, doc_nombre_col: str):
    """Si el CSV ya existe, reconstruye los dicts de entidades/contratistas desde él."""
    log.info(f"  Reconstruyendo entidades/contratistas desde {csv_path.name} existente...")
    count = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            upsert_entidad(row.get(nit_col), row.get(nombre_col), row.get(depto_col))
            upsert_contratista(row.get(doc_col), None, row.get(doc_nombre_col))
            count += 1
    log.info(f"  → {count:,} filas escaneadas para reconstrucción")


def normalize_secop2_contratos():
    log.info("=== Normalizando SECOP II Contratos ===")
    out = OUT_DIR / "contratos_s2.csv"
    if out.exists():
        log.info("  contratos_s2.csv ya existe — escaneando para entidades/contratistas")
        repopulate_from_existing(out, "nit_entidad", "ordenador_gasto",
                                 None, "doc_contratista", "ordenador_gasto")
        return []
    rows = []

    for raw in iter_chunks("secop2_contratos"):
        nit_e   = clean_nit(raw.get("nit_entidad", ""))
        nom_e   = clean_name(raw.get("nombre_entidad", ""))
        doc_c   = clean_nit(raw.get("documento_proveedor", ""))
        nom_c   = clean_name(raw.get("proveedor_adjudicado", ""))
        rep_l   = clean_name(raw.get("nombre_representante_legal", ""))
        id_rep  = clean_nit(raw.get("identificaci_n_representante_legal", ""))
        valor   = parse_value(raw.get("valor_del_contrato", ""))
        pagado  = parse_value(raw.get("valor_pagado", ""))
        pendiente = parse_value(raw.get("valor_pendiente_de_ejecucion", ""))
        f_firma = parse_date(raw.get("fecha_de_firma", ""))
        f_ini   = parse_date(raw.get("fecha_de_inicio_del_contrato", ""))
        f_fin   = parse_date(raw.get("fecha_de_fin_del_contrato", ""))
        es_pyme = null(raw.get("es_pyme", ""))
        modalidad = null(raw.get("modalidad_de_contratacion", ""))
        tipo    = null(raw.get("tipo_de_contrato", ""))
        estado  = null(raw.get("estado_contrato", ""))
        objeto  = null(raw.get("objeto_del_contrato", "") or raw.get("descripcion_del_proceso", ""))
        sector  = null(raw.get("sector", ""))
        orden_e = null(raw.get("orden", ""))
        depto   = null(raw.get("departamento", ""))
        ciudad  = null(raw.get("ciudad", ""))
        fuente  = "SGR" if parse_value(raw.get("sistema_general_de_regal_as","")) else \
                  "PGN" if parse_value(raw.get("presupuesto_general_de_la_nacion_pgn","")) else \
                  "PROPIO"
        ordenador = clean_name(raw.get("nombre_ordenador_del_gasto", ""))
        supervisor = clean_name(raw.get("nombre_supervisor", ""))
        num_doc_ordenador = clean_nit(raw.get("n_mero_de_documento_ordenador_del_gasto", ""))
        dias_add = parse_value(raw.get("dias_adicionados", ""))
        id_contrato = null(raw.get("id_contrato", ""))

        upsert_entidad(nit_e, nom_e, depto, ciudad, sector, orden_e)
        upsert_contratista(doc_c, null(raw.get("tipodocproveedor","")), nom_c,
                           rep_l, id_rep, es_pyme)

        if not id_contrato:
            continue

        rows.append({
            "id_contrato":      id_contrato,
            "nit_entidad":      nit_e,
            "doc_contratista":  doc_c,
            "valor":            valor,
            "valor_pagado":     pagado,
            "valor_pendiente":  pendiente,
            "estado":           estado,
            "modalidad":        modalidad,
            "tipo":             tipo,
            "objeto":           objeto[:300] if objeto else None,
            "fecha_firma":      f_firma,
            "fecha_inicio":     f_ini,
            "fecha_fin":        f_fin,
            "anio":             year_of(f_firma or f_ini),
            "fuente_recursos":  fuente,
            "dias_adicionados": int(dias_add) if dias_add else 0,
            "ordenador_gasto":  ordenador,
            "doc_ordenador":    num_doc_ordenador,
            "supervisor":       supervisor,
            "es_pyme":          es_pyme,
            "proceso_id":       null(raw.get("proceso_de_compra", "")),
        })

    write_csv(OUT_DIR / "contratos_s2.csv", rows, list(rows[0].keys()) if rows else [])
    return rows


# ── 2. SECOP II — Procesos ─────────────────────────────────────────────────────

def normalize_secop2_procesos():
    log.info("=== Normalizando SECOP II Procesos ===")
    out = OUT_DIR / "procesos_s2.csv"
    if out.exists():
        log.info("  procesos_s2.csv ya existe — escaneando para entidades/contratistas")
        repopulate_from_existing(out, "nit_entidad", "adjudicador",
                                 "depto_entidad", "doc_adjudicado", "adjudicador")
        return []
    rows = []

    for raw in iter_chunks("secop2_procesos"):
        nit_e      = clean_nit(raw.get("nit_entidad", ""))
        nom_e      = clean_name(raw.get("entidad", ""))
        doc_prov   = clean_nit(raw.get("nit_del_proveedor_adjudicado", ""))
        nom_prov   = clean_name(raw.get("nombre_del_proveedor", ""))
        id_proc    = null(raw.get("id_del_proceso", ""))
        precio_base = parse_value(raw.get("precio_base", ""))
        val_adj    = parse_value(raw.get("valor_total_adjudicacion", ""))
        modalidad  = null(raw.get("modalidad_de_contratacion", ""))
        estado     = null(raw.get("estado_resumen", ""))
        adjudicado = null(raw.get("adjudicado", ""))
        f_pub      = parse_date(raw.get("fecha_de_publicacion_del", ""))
        f_adj      = parse_date(raw.get("fecha_adjudicacion", ""))
        inv        = parse_value(raw.get("proveedores_invitados", ""))
        resp       = parse_value(raw.get("respuestas_al_procedimiento", ""))
        tipo       = null(raw.get("tipo_de_contrato", ""))
        desc       = null(raw.get("descripci_n_del_procedimiento", ""))
        depto      = null(raw.get("departamento_entidad", ""))
        adjudicador = clean_name(raw.get("nombre_del_adjudicador", ""))

        upsert_entidad(nit_e, nom_e, depto)
        if doc_prov:
            upsert_contratista(doc_prov, "NIT", nom_prov)

        if not id_proc:
            continue

        # FLAG: único oferente
        unico_oferente = (resp is not None and resp <= 1 and
                          val_adj is not None and val_adj > 0)

        rows.append({
            "id_proceso":       id_proc,
            "nit_entidad":      nit_e,
            "doc_adjudicado":   doc_prov,
            "precio_base":      precio_base,
            "valor_adjudicado": val_adj,
            "modalidad":        modalidad,
            "tipo_contrato":    tipo,
            "estado":           estado,
            "adjudicado":       adjudicado,
            "fecha_publicacion":f_pub,
            "fecha_adjudicacion":f_adj,
            "anio":             year_of(f_pub),
            "proveedores_invitados": int(inv) if inv else 0,
            "respuestas":       int(resp) if resp else 0,
            "unico_oferente":   unico_oferente,
            "adjudicador":      adjudicador,
            "descripcion":      desc[:300] if desc else None,
            "depto_entidad":    depto,
        })

    write_csv(OUT_DIR / "procesos_s2.csv", rows, list(rows[0].keys()) if rows else [])
    return rows


# ── 3. SECOP Integrado (legacy) ───────────────────────────────────────────────

def normalize_secop_integrado():
    log.info("=== Normalizando SECOP Integrado (legacy) ===")
    rows = []

    for raw in iter_chunks("secop_integrado"):
        nit_e   = clean_nit(raw.get("nit_de_la_entidad", ""))
        nom_e   = clean_name(raw.get("nombre_de_la_entidad", ""))
        doc_c   = clean_nit(raw.get("documento_proveedor", ""))
        nom_c   = clean_name(raw.get("nom_raz_social_contratista", ""))
        valor   = parse_value(raw.get("valor_contrato", ""))
        f_firma = parse_date(raw.get("fecha_de_firma_del_contrato", ""))
        f_ini   = parse_date(raw.get("fecha_inicio_ejecuci_n", ""))
        f_fin   = parse_date(raw.get("fecha_fin_ejecuci_n", ""))
        modalidad = null(raw.get("modalidad_de_contrataci_n", ""))
        tipo    = null(raw.get("tipo_de_contrato", ""))
        estado  = null(raw.get("estado_del_proceso", ""))
        objeto  = null(raw.get("objeto_a_contratar", "") or raw.get("objeto_del_proceso", ""))
        depto   = null(raw.get("departamento_entidad", ""))
        mpio    = null(raw.get("municipio_entidad", ""))
        nivel   = null(raw.get("nivel_entidad", ""))
        num_c   = null(raw.get("numero_del_contrato", ""))

        upsert_entidad(nit_e, nom_e, depto, mpio)
        upsert_contratista(doc_c, null(raw.get("tipo_documento_proveedor", "")), nom_c)

        if not num_c and not nit_e:
            continue

        rows.append({
            "numero_contrato":  num_c,
            "nit_entidad":      nit_e,
            "doc_contratista":  doc_c,
            "valor":            valor,
            "estado":           estado,
            "modalidad":        modalidad,
            "tipo":             tipo,
            "objeto":           objeto[:300] if objeto else None,
            "fecha_firma":      f_firma,
            "fecha_inicio":     f_ini,
            "fecha_fin":        f_fin,
            "anio":             year_of(f_firma or f_ini),
            "departamento":     depto,
            "municipio":        mpio,
            "origen":           "SECOP_I",
        })

    write_csv(OUT_DIR / "contratos_legacy.csv", rows, list(rows[0].keys()) if rows else [])
    return rows


# ── 4. SECOP II BPIN ──────────────────────────────────────────────────────────

def normalize_bpin():
    log.info("=== Normalizando SECOP II BPIN ===")
    rows = []
    for raw in iter_chunks("secop2_bpin"):
        rows.append({
            "id_proceso":    null(raw.get("id_proceso", "")),
            "id_contrato":   null(raw.get("id_contracto", "")),
            "codigo_bpin":   null(raw.get("codigo_bpin", "")),
            "anno_bpin":     null(raw.get("anno_bpin", "")),
            "id_portafolio": null(raw.get("id_portafolio", "")),
            "validacion":    null(raw.get("validacion_bpin", "")),
        })
    rows = [r for r in rows if any(v for v in r.values())]
    write_csv(OUT_DIR / "bpin.csv", rows, list(rows[0].keys()) if rows else [])


# ── 5. SGR ────────────────────────────────────────────────────────────────────

def normalize_sgr():
    log.info("=== Normalizando SGR ===")
    rows = []
    for raw in iter_chunks("sgr_ingresos"):
        row = {k: null(v) for k, v in raw.items()}
        rows.append(row)
    if rows:
        write_csv(OUT_DIR / "sgr_ingresos.csv", rows, list(rows[0].keys()))

    rows2 = []
    for raw in iter_chunks("sgr_giros"):
        row = {k: null(v) for k, v in raw.items()}
        rows2.append(row)
    if rows2:
        write_csv(OUT_DIR / "sgr_giros.csv", rows2, list(rows2[0].keys()))


# ── 6. Guardar nodos deduplicados ─────────────────────────────────────────────

def write_nodes():
    log.info("=== Escribiendo nodos deduplicados ===")
    ents = list(entidades.values())
    write_csv(OUT_DIR / "entidades.csv", ents,
              ["nit", "nombre", "departamento", "ciudad", "sector", "orden"])

    conts = list(contratistas.values())
    write_csv(OUT_DIR / "contratistas.csv", conts,
              ["doc_id", "tipo_doc", "nombre", "rep_legal", "id_rep_legal", "es_pyme", "nacionalidad"])

    # Stats
    log.info(f"  Entidades únicas:    {len(ents):,}")
    log.info(f"  Contratistas únicos: {len(conts):,}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("NORMALIZACIÓN — DATOS ANTICORRUPCIÓN COLOMBIA")
    log.info(f"Inicio: {datetime.now().isoformat()}")
    log.info("=" * 60)

    normalize_secop2_contratos()
    normalize_secop2_procesos()
    normalize_secop_integrado()
    normalize_bpin()
    normalize_sgr()
    write_nodes()

    log.info("=" * 60)
    log.info(f"COMPLETADO: {datetime.now().isoformat()}")
    log.info(f"Archivos en: {OUT_DIR}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
