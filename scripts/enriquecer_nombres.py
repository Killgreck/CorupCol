"""
Construye diccionarios doc_id→nombre y nit→nombre desde los datos crudos
y enriquece el reporte limpio con los nombres reales.
"""
import json
import gzip
import csv
import io
from pathlib import Path
import os

REPORTE_ENTRADA = Path("/home/apolo/A/CorupCol/reports/anomalias_2026-03-05_limpio.json")
REPORTE_SALIDA  = Path("/home/apolo/A/CorupCol/reports/anomalias_2026-03-05_final.json")

DATA = Path("/home/apolo/A/CorupCol/data")

# doc_id (proveedor) → nombre
contratistas_nombre = {}
# nit (entidad) → nombre
entidades_nombre = {}
# id_contrato (SECOP II) → {entidad, contratista}
contratos_sobrecosto = {}


def limpiar(s):
    return (s or "").strip().title() if s else ""


def cargar_secop2():
    """SECOP II: documento_proveedor → proveedor_adjudicado, nit_entidad → nombre_entidad"""
    carpeta = DATA / "secop2_contratos"
    archivos = sorted(carpeta.glob("*.csv.gz"))
    print(f"Leyendo {len(archivos)} chunks de SECOP II...")
    for i, f in enumerate(archivos):
        with gzip.open(f, "rt", encoding="utf-8", errors="replace") as gz:
            reader = csv.DictReader(gz)
            for row in reader:
                doc = (row.get("documento_proveedor") or "").strip()
                nombre_c = limpiar(row.get("proveedor_adjudicado"))
                if doc and nombre_c and doc not in contratistas_nombre:
                    contratistas_nombre[doc] = nombre_c

                nit = (row.get("nit_entidad") or "").strip()
                nombre_e = limpiar(row.get("nombre_entidad"))
                if nit and nombre_e and nit not in entidades_nombre:
                    entidades_nombre[nit] = nombre_e

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(archivos)} chunks — contratistas: {len(contratistas_nombre):,}, entidades: {len(entidades_nombre):,}")

    print(f"  SECOP II listo: {len(contratistas_nombre):,} contratistas, {len(entidades_nombre):,} entidades")


def cargar_secop1():
    """SECOP I: documento_proveedor → nom_raz_social_contratista, nit_de_la_entidad → nombre_de_la_entidad"""
    carpeta = DATA / "secop_integrado"
    archivos = sorted(carpeta.glob("*.csv.gz"))
    print(f"Leyendo {len(archivos)} chunks de SECOP I...")
    for i, f in enumerate(archivos):
        with gzip.open(f, "rt", encoding="utf-8", errors="replace") as gz:
            reader = csv.DictReader(gz)
            for row in reader:
                doc = (row.get("documento_proveedor") or "").strip()
                nombre_c = limpiar(row.get("nom_raz_social_contratista"))
                if doc and nombre_c and doc not in contratistas_nombre:
                    contratistas_nombre[doc] = nombre_c

                nit = (row.get("nit_de_la_entidad") or "").strip()
                nombre_e = limpiar(row.get("nombre_de_la_entidad"))
                if nit and nombre_e and nit not in entidades_nombre:
                    entidades_nombre[nit] = nombre_e

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(archivos)} chunks")

    print(f"  SECOP I listo: {len(contratistas_nombre):,} contratistas, {len(entidades_nombre):,} entidades")


def cargar_secop2_sobrecostos(target_ids):
    """Busca nombres de entidad y contratista para contratos de sobrecosto por id_contrato."""
    carpeta = DATA / "secop2_contratos"
    archivos = sorted(carpeta.glob("*.csv.gz"))
    remaining = set(target_ids)
    print(f"Buscando {len(remaining)} IDs de sobrecosto en {len(archivos)} chunks de SECOP II...")
    for i, f in enumerate(archivos):
        if not remaining:
            break
        with gzip.open(f, "rt", encoding="utf-8", errors="replace") as gz:
            reader = csv.DictReader(gz)
            for row in reader:
                cid = (row.get("id_contrato") or "").strip()
                if cid in remaining:
                    contratos_sobrecosto[cid] = {
                        "entidad": limpiar(row.get("nombre_entidad")),
                        "contratista": limpiar(row.get("proveedor_adjudicado")),
                    }
                    remaining.discard(cid)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(archivos)} chunks — encontrados: {len(contratos_sobrecosto)}, pendientes: {len(remaining)}")
    print(f"  Sobrecostos resueltos: {len(contratos_sobrecosto)}/{len(target_ids)} ({len(remaining)} sin nombre)")


def enriquecer_fila(fila, mapeo_contratista_keys, mapeo_entidad_keys):
    for key in mapeo_contratista_keys:
        doc = str(fila.get(key) or "").strip()
        if doc and doc in contratistas_nombre:
            fila["_nombre_contratista"] = contratistas_nombre[doc]
            break
    for key in mapeo_entidad_keys:
        nit = str(fila.get(key) or "").strip()
        if nit and nit in entidades_nombre:
            fila["_nombre_entidad"] = entidades_nombre[nit]
            break
    return fila


def main():
    cargar_secop2()
    cargar_secop1()

    with open(REPORTE_ENTRADA, encoding="utf-8") as f:
        reporte = json.load(f)

    anomalias = reporte["anomalias"]

    # Cargar nombres para sobrecostos usando id_contrato → SECOP II
    sobrecostos_raw = anomalias.get("sobrecosto_prorrogado", [])
    target_ids = [s.get("ct.id", "") for s in sobrecostos_raw if s.get("ct.id")]
    if target_ids:
        cargar_secop2_sobrecostos(target_ids)

    # Enriquecer cada sección
    for fila in anomalias.get("empresa_reciente_contrato_millonario", []):
        enriquecer_fila(fila, ["c.doc_id"], [])

    for fila in anomalias.get("carrusel_contratista_multiples_entidades", []):
        enriquecer_fila(fila, ["c.doc_id"], [])

    for fila in anomalias.get("nepotismo_ordenador_recurrente", []):
        enriquecer_fila(fila, ["c.doc_id"], [])

    for fila in anomalias.get("sobrecosto_prorrogado", []):
        # Rellenar entidad_nombre y contratista_nombre desde el índice de SECOP II
        ct_id = (fila.get("ct.id") or "").strip()
        if ct_id and ct_id in contratos_sobrecosto:
            if not fila.get("entidad_nombre"):
                fila["entidad_nombre"] = contratos_sobrecosto[ct_id]["entidad"]
            if not fila.get("contratista_nombre"):
                fila["contratista_nombre"] = contratos_sobrecosto[ct_id]["contratista"]
        enriquecer_fila(fila, [], [])

    with open(REPORTE_SALIDA, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"\nReporte final guardado en: {REPORTE_SALIDA}")

    # Imprimir resumen
    print("\n" + "="*65)
    print("TOP CASOS — CON NOMBRES REALES")
    print("="*65)

    casos = anomalias.get("empresa_reciente_contrato_millonario", [])[:10]
    if casos:
        print("\n📌 CONTRATISTAS CON MÁS VALOR ACUMULADO:")
        for c in casos:
            nombre = c.get("_nombre_contratista") or c.get("c.nombre") or "(sin nombre)"
            doc = c["c.doc_id"]
            valor = c["total_ganado"] / 1e9
            n = c["num_contratos"]
            print(f"  {doc:<15} {nombre[:45]:<45} ${valor:>10,.1f}B  ({n} contratos)")

    casos = anomalias.get("carrusel_contratista_multiples_entidades", [])[:10]
    if casos:
        print("\n🔄 CARRUSEL — CONTRATISTA EN MÚLTIPLES ENTIDADES:")
        for c in casos:
            nombre = c.get("_nombre_contratista") or c.get("c.nombre") or "(sin nombre)"
            doc = c["c.doc_id"]
            ents = c["entidades_distintas"]
            valor = c["total_valor"] / 1e9
            print(f"  {doc:<15} {nombre[:45]:<45} {ents:>3} entidades  ${valor:>8,.1f}B")

    casos = anomalias.get("nepotismo_ordenador_recurrente", [])[:10]
    if casos:
        print("\n👥 ORDENADOR RECURRENTE CON MISMO CONTRATISTA:")
        for c in casos:
            nombre_p = c.get("p.nombre") or "(sin nombre)"
            nombre_c = c.get("_nombre_contratista") or c.get("contratista_nombre") or "(sin nombre)"
            n = c["contratos_juntos"]
            valor = c["valor_total"] / 1e6
            print(f"  {nombre_p[:35]:<35} → {nombre_c[:35]:<35} {n:>4} contratos  ${valor:>8,.0f}M")

    casos = anomalias.get("sobrecosto_prorrogado", [])[:10]
    if casos:
        print("\n⏱️  CONTRATOS CON PRÓRROGA EXCESIVA:")
        for c in casos:
            entidad = c.get("entidad_nombre") or c.get("_nombre_entidad") or "(sin nombre)"
            contratista = c.get("contratista_nombre") or c.get("_nombre_contratista") or "(sin nombre)"
            dias = c["ct.dias_adicionados"]
            valor = c["ct.valor"] / 1e6
            objeto = (c.get("ct.objeto") or "")[:55]
            print(f"  {entidad[:35]:<35} | {contratista[:30]:<30}")
            print(f"    {dias} días | ${valor:,.0f}M | {objeto}")


if __name__ == "__main__":
    main()
