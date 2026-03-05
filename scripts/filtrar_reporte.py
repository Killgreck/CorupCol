"""
Filtra falsos positivos del reporte de anomalías y genera una versión limpia.
"""
import json
import re
from pathlib import Path

REPORTE_ENTRADA = Path("/home/apolo/A/CorupCol/reports/anomalias_2026-03-05.json")
REPORTE_SALIDA  = Path("/home/apolo/A/CorupCol/reports/anomalias_2026-03-05_limpio.json")

# Documentos placeholder / genéricos a descartar
DOC_BASURA = {
    "0", "1", "123456", "1234567", "12345678", "123456789",
    "000000", "0000000", "00000000", "000000000",
    "111111", "1111111", "11111111", "111111111",
    "999999", "9999999", "99999999", "999999999",
    "222222", "333333", "444444", "555555", "666666", "777777", "888888",
}

# Valor máximo razonable por contratista (100 billones COP — margen muy generoso)
MAX_VALOR = 100_000_000_000_000

# Prórroga máxima razonable: 5 años
MAX_DIAS_PRORROGA = 365 * 5


def doc_es_basura(doc_id: str) -> bool:
    if not doc_id:
        return True
    doc = str(doc_id).strip()
    if doc in DOC_BASURA:
        return True
    # Documentos con menos de 5 dígitos
    if re.fullmatch(r"\d{1,4}", doc):
        return True
    # Documentos con todos los dígitos iguales (ej. 55555555)
    if re.fullmatch(r"(\d)\1{4,}", doc):
        return True
    return False


def limpiar_empresa_reciente(filas):
    limpias = []
    for f in filas:
        if doc_es_basura(f.get("c.doc_id")):
            continue
        if f.get("total_ganado", 0) > MAX_VALOR:
            continue
        limpias.append(f)
    return limpias


def limpiar_carrusel(filas):
    limpias = []
    for f in filas:
        if doc_es_basura(f.get("c.doc_id")):
            continue
        if f.get("total_valor", 0) > MAX_VALOR:
            continue
        limpias.append(f)
    return limpias


def limpiar_nepotismo(filas):
    limpias = []
    for f in filas:
        if doc_es_basura(f.get("p.doc_id")):
            continue
        if doc_es_basura(f.get("c.doc_id")):
            continue
        if f.get("valor_total", 0) > MAX_VALOR:
            continue
        limpias.append(f)
    return limpias


def limpiar_sobrecosto(filas):
    limpias = []
    for f in filas:
        dias = f.get("ct.dias_adicionados", 0) or 0
        if dias > MAX_DIAS_PRORROGA:
            continue
        if f.get("ct.valor", 0) > MAX_VALOR:
            continue
        limpias.append(f)
    return limpias


FILTROS = {
    "empresa_reciente_contrato_millonario":    limpiar_empresa_reciente,
    "carrusel_contratista_multiples_entidades": limpiar_carrusel,
    "licitaciones_unico_oferente":             lambda x: x,
    "nepotismo_ordenador_recurrente":          limpiar_nepotismo,
    "autocontratacion_directa":               lambda x: x,
    "sobrecosto_prorrogado":                   limpiar_sobrecosto,
}


def main():
    with open(REPORTE_ENTRADA, encoding="utf-8") as f:
        reporte = json.load(f)

    anomalias_originales = reporte["anomalias"]
    anomalias_limpias = {}

    print("=== FILTRADO DE FALSOS POSITIVOS ===\n")
    for nombre, filas in anomalias_originales.items():
        filtro = FILTROS.get(nombre, lambda x: x)
        limpias = filtro(filas)
        descartadas = len(filas) - len(limpias)
        anomalias_limpias[nombre] = limpias
        print(f"[{nombre}]")
        print(f"  Original: {len(filas):>4}  →  Limpios: {len(limpias):>4}  (descartados: {descartadas})")

    reporte["anomalias"] = anomalias_limpias
    reporte["metadata"]["filtrado"] = True

    with open(REPORTE_SALIDA, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"\nReporte limpio guardado en: {REPORTE_SALIDA}")

    # Mostrar top casos reales por categoría
    print("\n" + "="*60)
    print("TOP CASOS REALES")
    print("="*60)

    # Empresa reciente millonaria
    casos = anomalias_limpias.get("empresa_reciente_contrato_millonario", [])[:5]
    if casos:
        print("\n📌 CONTRATISTAS CON MÁS CONTRATOS ACUMULADOS:")
        for c in casos:
            nombre = c.get("c.nombre") or "(sin nombre)"
            doc = c["c.doc_id"]
            valor = c["total_ganado"] / 1e9
            n = c["num_contratos"]
            print(f"  {doc} | {nombre[:40]} | ${valor:,.1f}B | {n} contratos")

    # Carrusel
    casos = anomalias_limpias.get("carrusel_contratista_multiples_entidades", [])[:5]
    if casos:
        print("\n🔄 CARRUSEL — CONTRATISTA EN MÚLTIPLES ENTIDADES:")
        for c in casos:
            nombre = c.get("c.nombre") or "(sin nombre)"
            doc = c["c.doc_id"]
            ents = c["entidades_distintas"]
            valor = c["total_valor"] / 1e9
            print(f"  {doc} | {nombre[:40]} | {ents} entidades | ${valor:,.1f}B")

    # Nepotismo
    casos = anomalias_limpias.get("nepotismo_ordenador_recurrente", [])[:5]
    if casos:
        print("\n👥 ORDENADOR RECURRENTE CON MISMO CONTRATISTA:")
        for c in casos:
            nombre_p = c.get("p.nombre") or "(sin nombre)"
            nombre_c = c.get("contratista_nombre") or "(sin nombre)"
            doc_p = c["p.doc_id"]
            n = c["contratos_juntos"]
            valor = c["valor_total"] / 1e6
            print(f"  {doc_p} {nombre_p[:30]} → {nombre_c[:30]} | {n} contratos | ${valor:,.0f}M")

    # Sobrecosto
    casos = anomalias_limpias.get("sobrecosto_prorrogado", [])[:5]
    if casos:
        print("\n⏱️  CONTRATOS CON PRÓRROGA EXCESIVA (>180 días):")
        for c in casos:
            entidad = c.get("entidad_nombre") or "(sin nombre)"
            contratista = c.get("contratista_nombre") or "(sin nombre)"
            dias = c["ct.dias_adicionados"]
            valor = c["ct.valor"] / 1e6
            objeto = (c.get("ct.objeto") or "")[:60]
            print(f"  {entidad[:30]} → {contratista[:30]}")
            print(f"    {dias} días extra | ${valor:,.0f}M | {objeto}")


if __name__ == "__main__":
    main()
