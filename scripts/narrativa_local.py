#!/usr/bin/env python3
"""
Generador de narrativas LOCAL (sin API de Claude).
Produce narrativas basadas en plantillas a partir de anomalias_final.json.
Cuando tengas ANTHROPIC_API_KEY configurada, usa narrativa_claude.py en su lugar.
"""
import json
import re
from pathlib import Path

REPORTE = Path("/home/apolo/A/CorupCol/reports/anomalias_con_fechas.json")
SALIDA  = Path("/home/apolo/A/CorupCol/dashboard/data/narrativas.json")


def clean(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    return s.title() if s else None


def fmt_valor(valor_pesos):
    b = valor_pesos / 1_000_000_000_000
    if b >= 1:
        return f"${b:,.1f} billones COP"
    mm = valor_pesos / 1_000_000_000
    if mm >= 1:
        return f"${mm:,.0f} mil millones COP"
    m = valor_pesos / 1_000_000
    return f"${m:,.0f} millones COP"


def narrativa_carrusel(caso):
    nombre = clean(caso.get("_nombre_contratista") or caso.get("c.nombre")) or f"NIT {caso.get('c.doc_id','?')}"
    nit    = caso.get("c.doc_id", "N/D")
    entid  = caso.get("entidades_distintas", 0)
    ncontr = caso.get("total_contratos", 0)
    valor  = fmt_valor(caso.get("total_valor", 0))

    narrativa = (
        f"{nombre} (NIT/Cédula: {nit}) registra {ncontr} contratos con {entid} entidades "
        f"públicas distintas, acumulando {valor} en contratación estatal según SECOP I y II. "
        f"La distribución simultánea en múltiples agencias del Estado es un patrón típico del "
        f"\"carrusel de contratos\", donde se elude la vigilancia jerárquica interna. "
        f"Se recomienda verificar si los contratos superan individualmente los topes de mínima cuantía "
        f"y si el objeto contractual se repite entre distintas entidades."
    )
    return {
        "tipo": "carrusel",
        "contratista": nombre,
        "doc_id": nit,
        "entidades": entid,
        "contratos": ncontr,
        "valor_b": round(caso.get("total_valor", 0) / 1e12, 1),
        "fecha": caso.get("fecha_inicio"),
        "fecha_inicio": caso.get("fecha_inicio"),
        "fecha_fin": caso.get("fecha_fin"),
        "narrativa": narrativa,
    }


def narrativa_nepotismo(caso):
    ordenador  = clean(caso.get("p.nombre")) or f"CC {caso.get('p.doc_id','?')}"
    doc_ord    = caso.get("p.doc_id", "N/D")
    contratista = clean(caso.get("_nombre_contratista") or caso.get("contratista_nombre")) or f"NIT {caso.get('c.doc_id','?')}"
    n          = caso.get("contratos_juntos", 0)
    valor      = fmt_valor(caso.get("valor_total", 0))

    narrativa = (
        f"El ordenador del gasto {ordenador} (CC: {doc_ord}) ha adjudicado o aprobado {n} contratos "
        f"recurrentes al mismo contratista, {contratista}, por un valor total de {valor} según SECOP II. "
        f"La alta recurrencia entre un mismo funcionario y un mismo proveedor puede indicar direccionamiento "
        f"en la selección, lo que viola el principio de transparencia de la Ley 80 de 1993. "
        f"Se sugiere revisar si hubo pluralidad de oferentes y si el funcionario tiene vínculos "
        f"personales o familiares con el contratista."
    )
    return {
        "tipo": "nepotismo",
        "ordenador": ordenador,
        "doc_ordenador": doc_ord,
        "contratista": contratista,
        "contratos": n,
        "valor_m": round(caso.get("valor_total", 0) / 1e6, 0),
        "fecha": caso.get("fecha_inicio"),
        "fecha_inicio": caso.get("fecha_inicio"),
        "fecha_fin": caso.get("fecha_fin"),
        "narrativa": narrativa,
    }


def narrativa_autocontratacion(caso):
    funcionario  = clean(caso.get("p.nombre")) or f"CC {caso.get('p.doc_id','?')}"
    doc          = caso.get("p.doc_id", "N/D")
    empresa      = clean(caso.get("_nombre_contratista") or caso.get("contratista_nombre")) or "Empresa contratista"
    contrato_id  = caso.get("ct.id", "N/D")
    valor        = fmt_valor(caso.get("ct.valor", 0))
    fecha        = (caso.get("ct.fecha_firma") or "")[:10] or None

    narrativa = (
        f"{funcionario} (CC: {doc}) aparece simultáneamente como ordenador del gasto en la entidad "
        f"contratante y como representante legal o socio de {empresa}, que recibió el contrato {contrato_id} "
        f"por valor de {valor}. "
        f"Esta situación constituye una posible autocontratación prohibida por el artículo 8 de la Ley 80 "
        f"de 1993, que prohíbe a los servidores públicos celebrar contratos con entidades donde tengan "
        f"interés económico. La Contraloría General puede verificar este conflicto de interés."
    )
    return {
        "tipo": "autocontratacion",
        "funcionario": funcionario,
        "doc_id": doc,
        "empresa": empresa,
        "contrato_id": contrato_id,
        "valor_m": round(caso.get("ct.valor", 0) / 1e6, 0),
        "fecha": fecha,
        "fecha_inicio": fecha,
        "fecha_fin": caso.get("fecha_fin"),
        "narrativa": narrativa,
    }


def narrativa_sobrecosto(caso):
    entidad     = clean(caso.get("entidad_nombre")) or "Entidad pública"
    contratista = clean(caso.get("contratista_nombre") or caso.get("_nombre_contratista")) or "Contratista"
    contrato_id = caso.get("ct.id", "N/D")
    dias        = caso.get("ct.dias_adicionados", 0)
    anios       = round(dias / 365, 1)
    valor       = fmt_valor(caso.get("ct.valor", 0))
    objeto      = (caso.get("ct.objeto") or "No especificado")[:150]

    narrativa = (
        f"El contrato {contrato_id} entre {entidad} y {contratista}, valorado en {valor}, "
        f"acumula {dias:,} días de prórroga ({anios} años adicionales al plazo original). "
        f"Objeto del contrato: \"{objeto}\". "
        f"Las adiciones de tiempo excesivas suelen encubrir sobrecostos no declarados o deficiencias "
        f"en la planeación inicial. La Contraloría puede revisar si las prórrogas fueron justificadas "
        f"documentalmente y si implicaron mayores valores."
    )
    return {
        "tipo": "sobrecosto",
        "entidad": entidad,
        "contratista": contratista,
        "contrato_id": contrato_id,
        "dias_prorroga": dias,
        "valor_m": round(caso.get("ct.valor", 0) / 1e6, 0),
        "objeto": objeto,
        "fecha": caso.get("fecha_inicio"),
        "fecha_inicio": caso.get("fecha_inicio"),
        "fecha_fin": caso.get("fecha_fin"),
        "narrativa": narrativa,
    }


def narrativa_empresa_reciente(caso):
    nombre      = clean(caso.get("_nombre_contratista") or caso.get("c.nombre")) or f"NIT {caso.get('c.doc_id','?')}"
    nit         = caso.get("c.doc_id", "N/D")
    primer      = (caso.get("primer_contrato") or "")[:10]
    total       = fmt_valor(caso.get("total_ganado", 0))
    ncontr      = caso.get("num_contratos", 0)

    narrativa = (
        f"{nombre} (NIT: {nit}) obtuvo su primer contrato estatal el {primer} y desde entonces "
        f"ha acumulado {total} en {ncontr} contratos con el Estado colombiano según SECOP I y II. "
        f"Las empresas constituidas poco antes de recibir contratos millonarios son un indicador de "
        f"riesgo de corrupción, ya que pueden carecer de experiencia real o ser creadas instrumentalmente. "
        f"Se recomienda verificar en el RUES la fecha de constitución efectiva y los socios de la empresa."
    )
    return {
        "tipo": "empresa_reciente",
        "contratista": nombre,
        "doc_id": nit,
        "valor_b": round(caso.get("total_ganado", 0) / 1e12, 1),
        "contratos": ncontr,
        "fecha": primer,
        "fecha_inicio": primer,
        "fecha_fin": caso.get("fecha_fin"),
        "narrativa": narrativa,
    }


def main():
    with open(REPORTE, encoding="utf-8") as f:
        reporte = json.load(f)

    anomalias = reporte["anomalias"]
    narrativas = []

    print("Generando narrativas locales (sin API)...")

    for caso in anomalias.get("carrusel_contratista_multiples_entidades", [])[:10]:
        narrativas.append(narrativa_carrusel(caso))

    for caso in anomalias.get("nepotismo_ordenador_recurrente", [])[:10]:
        narrativas.append(narrativa_nepotismo(caso))

    for caso in anomalias.get("autocontratacion_directa", [])[:8]:
        narrativas.append(narrativa_autocontratacion(caso))

    for caso in anomalias.get("sobrecosto_prorrogado", [])[:8]:
        narrativas.append(narrativa_sobrecosto(caso))

    for caso in anomalias.get("empresa_reciente_contrato_millonario", [])[:8]:
        narrativas.append(narrativa_empresa_reciente(caso))

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(narrativas, f, ensure_ascii=False, indent=2)

    print(f"Generadas {len(narrativas)} narrativas → {SALIDA}")
    print()
    print("Tipos generados:")
    from collections import Counter
    c = Counter(n["tipo"] for n in narrativas)
    for tipo, cnt in c.items():
        print(f"  {tipo}: {cnt}")
    print()
    print("Cuando configures ANTHROPIC_API_KEY en .env,")
    print("ejecuta: python3 scripts/narrativa_claude.py")
    print("para reemplazar estas narrativas con análisis de IA.")


if __name__ == "__main__":
    main()
