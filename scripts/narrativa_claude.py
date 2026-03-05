"""
Análisis narrativo con Claude API para los top casos de anomalías.
Genera explicaciones en español listas para periodistas y las integra
en dashboard/data/narrativas.json y reports/resumen_ejecutivo.md
"""
import json
import os
from pathlib import Path
import anthropic

REPORTE = Path("/home/apolo/A/CorupCol/reports/anomalias_2026-03-05_final.json")
SALIDA_JSON = Path("/home/apolo/A/CorupCol/dashboard/data/narrativas.json")
SALIDA_MD = Path("/home/apolo/A/CorupCol/reports/resumen_ejecutivo.md")

from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-6"


def analizar(sistema: str, usuario: str) -> str:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": usuario}],
        system=sistema,
    )
    return msg.content[0].text.strip()


SISTEMA = """Eres un analista anticorrupción especializado en contratación pública colombiana.
Tu rol es explicar hallazgos de un sistema de detección automatizada a periodistas y ciudadanos.

Reglas estrictas:
- Escribe en español claro, sin jerga técnica
- NO afirmes que hay corrupción — di "presenta un patrón que merece investigación"
- Incluye siempre: qué se detectó, por qué es sospechoso, qué deberían investigar
- Sé conciso: máximo 4 oraciones por hallazgo
- Tono: serio, factual, sin sensacionalismo
- Los datos son de SECOP I/II (datos.gov.co) — fuente oficial del gobierno colombiano"""


def narrativa_carrusel(caso: dict) -> dict:
    nombre = caso.get("_nombre_contratista") or caso.get("c.nombre") or "Contratista sin nombre"
    nit = caso["c.doc_id"]
    entidades = caso["entidades_distintas"]
    contratos = caso["total_contratos"]
    valor_b = caso["total_valor"] / 1e9

    prompt = f"""Contratista: {nombre} (NIT/Cédula: {nit})
Contratos con el Estado: {contratos} contratos con {entidades} entidades públicas distintas
Valor total acumulado: ${valor_b:,.1f} miles de millones COP

Explica este patrón de "carrusel de contratos" en 3-4 oraciones para un periodista colombiano."""

    return {
        "tipo": "carrusel",
        "contratista": nombre,
        "doc_id": nit,
        "entidades": entidades,
        "valor_b": round(valor_b, 1),
        "narrativa": analizar(SISTEMA, prompt),
    }


def narrativa_nepotismo(caso: dict) -> dict:
    ordenador = caso.get("p.nombre") or "Funcionario desconocido"
    doc_ord = caso["p.doc_id"]
    contratista = caso.get("_nombre_contratista") or caso.get("contratista_nombre") or "Contratista sin nombre"
    n = caso["contratos_juntos"]
    valor_m = caso["valor_total"] / 1e6

    prompt = f"""Funcionario público (ordenador del gasto): {ordenador} (cédula: {doc_ord})
Contratos firmados con el mismo contratista: {n} contratos
Contratista beneficiado: {contratista}
Valor total de esos contratos: ${valor_m:,.0f} millones COP

Explica este patrón de "ordenador recurrente" en 3-4 oraciones. ¿Por qué es sospechoso que un funcionario siempre contrate con el mismo proveedor?"""

    return {
        "tipo": "nepotismo",
        "ordenador": ordenador,
        "doc_ordenador": doc_ord,
        "contratista": contratista,
        "contratos": n,
        "valor_m": round(valor_m, 0),
        "narrativa": analizar(SISTEMA, prompt),
    }


def narrativa_autocontratacion(caso: dict) -> dict:
    funcionario = caso.get("p.nombre") or "Funcionario desconocido"
    doc = caso["p.doc_id"]
    empresa = caso.get("_nombre_contratista") or caso.get("contratista_nombre") or "Empresa sin nombre"
    contrato_id = caso.get("ct.id", "")
    valor_m = (caso.get("ct.valor") or 0) / 1e6
    fecha = caso.get("ct.fecha_firma") or "fecha desconocida"

    prompt = f"""Funcionario público: {funcionario} (cédula: {doc})
Este funcionario aparece como ORDENADOR DEL GASTO en un contrato donde él mismo es REPRESENTANTE LEGAL del contratista.
Empresa contratista: {empresa}
Contrato ID: {contrato_id}
Valor: ${valor_m:,.0f} millones COP
Fecha: {fecha}

Explica en 3-4 oraciones por qué la autocontratación directa es un conflicto de interés grave bajo la ley colombiana."""

    return {
        "tipo": "autocontratacion",
        "funcionario": funcionario,
        "doc_id": doc,
        "empresa": empresa,
        "contrato_id": contrato_id,
        "valor_m": round(valor_m, 0),
        "narrativa": analizar(SISTEMA, prompt),
    }


def narrativa_sobrecosto(caso: dict) -> dict:
    entidad = caso.get("entidad_nombre") or "(entidad sin nombre)"
    contratista = caso.get("contratista_nombre") or caso.get("_nombre_contratista") or "(contratista sin nombre)"
    dias = caso["ct.dias_adicionados"]
    valor_m = caso["ct.valor"] / 1e6
    objeto = (caso.get("ct.objeto") or "")[:200]
    contrato_id = caso.get("ct.id", "")

    prompt = f"""Entidad contratante: {entidad}
Contratista: {contratista}
Contrato ID: {contrato_id}
Objeto: {objeto}
Valor original: ${valor_m:,.0f} millones COP
Días adicionales (prórroga): {dias} días ({dias//365} años aproximadamente)

Explica en 3-4 oraciones por qué una prórroga de {dias} días en un contrato público es una señal de alerta."""

    return {
        "tipo": "sobrecosto",
        "entidad": entidad,
        "contratista": contratista,
        "contrato_id": contrato_id,
        "dias_prorroga": dias,
        "valor_m": round(valor_m, 0),
        "objeto": objeto,
        "narrativa": analizar(SISTEMA, prompt),
    }


def generar_resumen_ejecutivo(narrativas: list, stats: dict) -> str:
    casos_texto = "\n\n".join([
        f"Caso {i+1} ({n['tipo'].upper()}): {n.get('narrativa','')}"
        for i, n in enumerate(narrativas[:5])
    ])

    prompt = f"""Se analizaron {stats.get('total_nodos',0):,} nodos y {stats.get('total_relaciones',0):,} relaciones
en el grafo de contratación pública colombiana (SECOP I y II, datos.gov.co).
Valor total de contratos analizados: $4,247 miles de millones COP.

Los 5 hallazgos más relevantes del análisis automatizado son:

{casos_texto}

Redacta un RESUMEN EJECUTIVO completo en Markdown con estas secciones exactas:
## ¿Qué es este sistema?
## Metodología (3 bullets)
## Los 5 hallazgos más críticos (con nombre, cifra y por qué es sospechoso)
## Cómo verificarlo (pasos para un periodista)
## Limitaciones del análisis
## Fuentes y código

Máximo 2 páginas. Tono formal pero accesible. Recuerda: no afirmar corrupción, sino "patrones que merecen investigación"."""

    return analizar(SISTEMA, prompt)


def main():
    with open(REPORTE, encoding="utf-8") as f:
        reporte = json.load(f)

    anomalias = reporte["anomalias"]
    stats = reporte["metadata"]["estadisticas_generales"]

    narrativas = []
    print("Generando narrativas con Claude API...\n")

    # Top 3 carrusel
    for caso in anomalias.get("carrusel_contratista_multiples_entidades", [])[:3]:
        print(f"  → Carrusel: {caso.get('_nombre_contratista') or caso['c.doc_id']}")
        narrativas.append(narrativa_carrusel(caso))

    # Top 3 nepotismo
    for caso in anomalias.get("nepotismo_ordenador_recurrente", [])[:3]:
        print(f"  → Nepotismo: {caso.get('p.nombre')}")
        narrativas.append(narrativa_nepotismo(caso))

    # Top 2 autocontratación
    for caso in anomalias.get("autocontratacion_directa", [])[:2]:
        print(f"  → Autocontratación: {caso.get('p.nombre')}")
        narrativas.append(narrativa_autocontratacion(caso))

    # Top 2 sobrecostos
    for caso in anomalias.get("sobrecosto_prorrogado", [])[:2]:
        print(f"  → Sobrecosto: {caso['ct.dias_adicionados']} días")
        narrativas.append(narrativa_sobrecosto(caso))

    # Guardar narrativas para el dashboard
    SALIDA_JSON.parent.mkdir(exist_ok=True)
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(narrativas, f, ensure_ascii=False, indent=2)
    print(f"\nNarrativas guardadas: {SALIDA_JSON}")

    # Generar resumen ejecutivo
    print("\nGenerando resumen ejecutivo...")
    resumen = generar_resumen_ejecutivo(narrativas, stats)

    with open(SALIDA_MD, "w", encoding="utf-8") as f:
        f.write("# Reporte Anticorrupción Colombia — Análisis Automatizado\n")
        f.write(f"**Generado:** 2026-03-05 | **Datos:** SECOP I/II, datos.gov.co\n\n")
        f.write(resumen)

    print(f"Resumen ejecutivo guardado: {SALIDA_MD}")

    # Preview
    print("\n" + "="*65)
    print("PREVIEW NARRATIVAS")
    print("="*65)
    for n in narrativas[:3]:
        print(f"\n[{n['tipo'].upper()}]")
        print(n["narrativa"])


if __name__ == "__main__":
    main()
