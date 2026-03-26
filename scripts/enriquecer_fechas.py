#!/usr/bin/env python3
"""
Enriquece anomalias_final.json con rangos de fechas (fecha_inicio, fecha_fin)
haciendo un único pase por los CSVs normalizados.
Salida: reports/anomalias_con_fechas.json
"""
import csv
import json
from pathlib import Path
from datetime import datetime

BASE      = Path("/home/apolo/A/CorupCol")
REPORTE   = BASE / "reports/anomalias_2026-03-05_final.json"
SALIDA    = BASE / "reports/anomalias_con_fechas.json"
LEGACY    = BASE / "normalized/contratos_legacy.csv"
S2        = BASE / "normalized/contratos_s2.csv"

# ── Cargar anomalías ──────────────────────────────────────────────────────────
print("Cargando anomalías…")
with open(REPORTE, encoding="utf-8") as f:
    reporte = json.load(f)

anomalias = reporte["anomalias"]

# ── Construir sets de búsqueda ────────────────────────────────────────────────
# carrusel/empresa_reciente → buscar por doc_contratista
nits_contratista = set()
for r in anomalias.get("carrusel_contratista_multiples_entidades", []):
    if r.get("c.doc_id"): nits_contratista.add(str(r["c.doc_id"]).strip())
for r in anomalias.get("empresa_reciente_contrato_millonario", []):
    if r.get("c.doc_id"): nits_contratista.add(str(r["c.doc_id"]).strip())

# nepotismo / autocontratacion → buscar por doc_ordenador
docs_ordenador = set()
for r in anomalias.get("nepotismo_ordenador_recurrente", []):
    if r.get("p.doc_id"): docs_ordenador.add(str(r["p.doc_id"]).strip())
for r in anomalias.get("autocontratacion_directa", []):
    if r.get("p.doc_id"): docs_ordenador.add(str(r["p.doc_id"]).strip())

# sobrecosto → buscar por id_contrato
ids_contrato = set()
for r in anomalias.get("sobrecosto_prorrogado", []):
    if r.get("ct.id"): ids_contrato.add(str(r["ct.id"]).strip())

print(f"  Buscando {len(nits_contratista)} NITs contratista")
print(f"  Buscando {len(docs_ordenador)} docs ordenador")
print(f"  Buscando {len(ids_contrato)} IDs contrato")

# ── Acumuladores de fechas ────────────────────────────────────────────────────
# {nit: {"min": date, "max": date}}
fechas_contratista = {}
fechas_ordenador   = {}
fechas_contrato    = {}

def upd(store, key, fi, ff):
    """Actualiza min/max de fechas para una clave."""
    if not key: return
    for raw in (fi, ff):
        if not raw or not raw.strip(): continue
        try:
            d = datetime.strptime(raw.strip()[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if key not in store:
            store[key] = {"min": d, "max": d}
        else:
            if d < store[key]["min"]: store[key]["min"] = d
            if d > store[key]["max"]: store[key]["max"] = d

def scan_csv(path, col_id_contr, col_id_ord, col_id_ct, col_fi, col_ff):
    """Pase único sobre un CSV."""
    count = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            count += 1
            if count % 2_000_000 == 0:
                print(f"    … {count:,} filas")

            fi = row.get(col_fi, "")
            ff = row.get(col_ff, "")

            nit = row.get(col_id_contr, "").strip()
            if nit and nit in nits_contratista:
                upd(fechas_contratista, nit, fi, ff)

            ord_doc = row.get(col_id_ord, "").strip() if col_id_ord else ""
            if ord_doc and ord_doc in docs_ordenador:
                upd(fechas_ordenador, ord_doc, fi, ff)

            ct_id = row.get(col_id_ct, "").strip() if col_id_ct else ""
            if ct_id and ct_id in ids_contrato:
                upd(fechas_contrato, ct_id, fi, ff)

    print(f"    Total: {count:,} filas")

print("\nEscaneando contratos_legacy.csv…")
scan_csv(LEGACY,
         col_id_contr="doc_contratista",
         col_id_ord=None,          # legacy no tiene ordenador
         col_id_ct="numero_contrato",
         col_fi="fecha_inicio",
         col_ff="fecha_fin")

print("\nEscaneando contratos_s2.csv…")
scan_csv(S2,
         col_id_contr="doc_contratista",
         col_id_ord="doc_ordenador",
         col_id_ct="id_contrato",
         col_fi="fecha_inicio",
         col_ff="fecha_fin")

def fmt(d):
    """Formatea fecha y sanea años absurdos del SECOP."""
    if not d:
        return None
    y = d.year
    # Typo clásico: 21xx donde debería ser 20xx (ej. 2116 → 2016)
    if y > 2040:
        corrected = y - 100
        if 1990 <= corrected <= 2035:
            d = d.replace(year=corrected)
        else:
            # Placeholder tipo 2100/2099 sin corrección obvia → omitir
            return None
    return d.strftime("%Y-%m-%d")

def get_rango_contratista(nit):
    k = str(nit).strip()
    r = fechas_contratista.get(k)
    return (fmt(r["min"]), fmt(r["max"])) if r else (None, None)

def get_rango_ordenador(doc):
    k = str(doc).strip()
    r = fechas_ordenador.get(k)
    return (fmt(r["min"]), fmt(r["max"])) if r else (None, None)

def get_rango_contrato(ct_id):
    k = str(ct_id).strip()
    r = fechas_contrato.get(k)
    return (fmt(r["min"]), fmt(r["max"])) if r else (None, None)

# ── Inyectar fechas en cada registro ─────────────────────────────────────────
print("\nInyectando fechas…")
enriquecidos = 0

for r in anomalias.get("carrusel_contratista_multiples_entidades", []):
    fi, ff = get_rango_contratista(r.get("c.doc_id", ""))
    r["fecha_inicio"], r["fecha_fin"] = fi, ff
    if fi: enriquecidos += 1

for r in anomalias.get("empresa_reciente_contrato_millonario", []):
    fi, ff = get_rango_contratista(r.get("c.doc_id", ""))
    # Para empresa reciente, inicio = primer contrato (ya lo tenemos)
    r["fecha_inicio"] = r.get("primer_contrato") or fi
    r["fecha_fin"]    = ff
    if ff: enriquecidos += 1

for r in anomalias.get("nepotismo_ordenador_recurrente", []):
    fi, ff = get_rango_ordenador(r.get("p.doc_id", ""))
    r["fecha_inicio"], r["fecha_fin"] = fi, ff
    if fi: enriquecidos += 1

for r in anomalias.get("autocontratacion_directa", []):
    fi, ff = get_rango_ordenador(r.get("p.doc_id", ""))
    r["fecha_inicio"] = r.get("ct.fecha_firma") or fi
    r["fecha_fin"]    = ff
    if fi: enriquecidos += 1

for r in anomalias.get("sobrecosto_prorrogado", []):
    fi, ff = get_rango_contrato(r.get("ct.id", ""))
    r["fecha_inicio"], r["fecha_fin"] = fi, ff
    if fi: enriquecidos += 1

# ── Guardar ───────────────────────────────────────────────────────────────────
with open(SALIDA, "w", encoding="utf-8") as f:
    json.dump(reporte, f, ensure_ascii=False)

print(f"\nListo: {enriquecidos} registros con fechas → {SALIDA}")
