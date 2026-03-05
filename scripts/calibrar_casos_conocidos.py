"""
Calibración del grafo contra casos de corrupción conocidos en Colombia.
Verifica que el sistema detecta los patrones documentados.

Casos:
  1. Odebrecht (NIT: 830079452) — sobornos en contratos de infraestructura
  2. Centros Poblados (NIT: 901143440) — $70,000M adjudicados sin garantías
  3. Ungrd contratos Hidroituango (entidad: 900364177) — carrusel de interventorías
  4. Proceso Ruta del Sol (Odebrecht + Corficolombiana)
"""
import json
import logging
from pathlib import Path
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("CALIBRACION")

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", ""))

CASOS = {
    "odebrecht": {
        "desc": "Odebrecht — sobornos en contratos de infraestructura vial",
        "nits": ["830079452", "830079452-1", "8300794520"],
        "ref": "Fiscalía Colombia 2017 — $11,000M USD en sobornos globales",
    },
    "centros_poblados": {
        "desc": "Centros Poblados — contrato internet rural $70,000M sin garantías",
        "nits": ["901143440", "9011434400"],
        "ref": "Contraloría GR 2021 — hallazgos fiscales $70,792M",
    },
    "ungrd_hidroituango": {
        "desc": "UNGRD — contratos de emergencia Hidroituango 2018",
        "nit_entidad": "900364177",
        "ref": "Contraloría GR 2019 — $1,200M en contratos directos de emergencia",
    },
    "corficolombiana_ruta_sol": {
        "desc": "Corficolombiana / Episol — Ruta del Sol Sector 2",
        "nits": ["860002964", "830122600"],
        "ref": "Proceso penal 2018 — $6.5 billones COP",
    },
}


def buscar_contratista(session, nit: str) -> dict:
    """Busca un contratista y todos sus contratos en el grafo."""
    result = session.run("""
        MATCH (c:Contratista {doc_id: $nit})
        OPTIONAL MATCH (c)-[g:GANÓ]->(ct:Contrato)
        OPTIONAL MATCH (e:Entidad)-[:FIRMÓ]->(ct)
        RETURN
            c.doc_id AS nit,
            c.nombre AS nombre,
            COUNT(ct) AS total_contratos,
            SUM(ct.valor) AS valor_total,
            MIN(ct.fecha_firma) AS primer_contrato,
            MAX(ct.fecha_firma) AS ultimo_contrato,
            COLLECT(DISTINCT e.nombre)[..5] AS entidades_muestra
    """, nit=nit)
    row = result.single()
    return dict(row) if row else None


def buscar_entidad(session, nit: str) -> dict:
    """Busca una entidad y sus contratos."""
    result = session.run("""
        MATCH (e:Entidad {nit: $nit})
        OPTIONAL MATCH (e)-[:FIRMÓ]->(ct:Contrato)
        OPTIONAL MATCH (c:Contratista)-[:GANÓ]->(ct)
        RETURN
            e.nit AS nit,
            e.nombre AS nombre,
            e.departamento AS departamento,
            COUNT(ct) AS total_contratos,
            SUM(ct.valor) AS valor_total,
            COLLECT(DISTINCT c.nombre)[..5] AS contratistas_muestra
    """, nit=nit)
    row = result.single()
    return dict(row) if row else None


def buscar_contratistas_entidad(session, nit_entidad: str, top: int = 10) -> list:
    """Top contratistas de una entidad por valor."""
    result = session.run("""
        MATCH (e:Entidad {nit: $nit})-[:FIRMÓ]->(ct:Contrato)<-[:GANÓ]-(c:Contratista)
        WITH c, COUNT(ct) AS contratos, SUM(ct.valor) AS valor
        RETURN c.doc_id AS nit_c, c.nombre AS nombre, contratos, valor
        ORDER BY valor DESC LIMIT $top
    """, nit=nit_entidad, top=top)
    return [dict(r) for r in result]


def buscar_anomalias_contratista(session, nit: str) -> dict:
    """Verifica qué anomalías activa un contratista específico."""
    anomalias = {}

    # Carrusel
    r = session.run("""
        MATCH (c:Contratista {doc_id: $nit})-[:GANÓ]->(ct:Contrato)<-[:FIRMÓ]-(e:Entidad)
        RETURN COUNT(DISTINCT e) AS entidades_distintas, COUNT(ct) AS total_contratos, SUM(ct.valor) AS total_valor
    """, nit=nit).single()
    if r:
        anomalias["carrusel"] = dict(r)

    # Prórrogas excesivas
    r2 = session.run("""
        MATCH (c:Contratista {doc_id: $nit})-[:GANÓ]->(ct:Contrato)
        WHERE ct.dias_adicionados > 180
        RETURN COUNT(ct) AS contratos_prorrogados, MAX(ct.dias_adicionados) AS max_dias, SUM(ct.valor) AS valor_prorrogado
    """, nit=nit).single()
    if r2 and r2["contratos_prorrogados"]:
        anomalias["prorrogas_excesivas"] = dict(r2)

    # Autocontratación (si ya cargamos rep_legal)
    r3 = session.run("""
        MATCH (p:Persona)-[:ES_REP_LEGAL_DE]->(c:Contratista {doc_id: $nit})
        MATCH (p)-[:ORDENÓ]->(ct:Contrato)<-[:GANÓ]-(c)
        RETURN COUNT(ct) AS autocontratos, SUM(ct.valor) AS valor_autocontratado
    """, nit=nit).single()
    if r3 and r3["autocontratos"]:
        anomalias["autocontratacion"] = dict(r3)

    return anomalias


def main():
    resultados = {}

    with driver.session() as session:
        print("\n" + "="*70)
        print("CALIBRACIÓN — CASOS DE CORRUPCIÓN CONOCIDOS")
        print("="*70)

        # --- Casos por NIT de contratista ---
        for caso_id, caso in CASOS.items():
            if "nit_entidad" in caso:
                continue  # los de entidad van después

            print(f"\n📋 {caso_id.upper()}")
            print(f"   {caso['desc']}")
            print(f"   Ref: {caso['ref']}")

            encontrado = False
            for nit in caso["nits"]:
                info = buscar_contratista(session, nit)
                if info and info.get("total_contratos", 0) > 0:
                    encontrado = True
                    valor_b = (info["valor_total"] or 0) / 1e9
                    print(f"   ✅ ENCONTRADO — NIT: {nit}")
                    print(f"      Nombre: {info.get('nombre') or '(sin nombre)'}")
                    print(f"      Contratos: {info['total_contratos']:,} | Valor: ${valor_b:,.1f}B")
                    print(f"      Rango: {info.get('primer_contrato')} → {info.get('ultimo_contrato')}")
                    if info.get("entidades_muestra"):
                        print(f"      Entidades: {', '.join([e for e in info['entidades_muestra'] if e])[:80]}")

                    anomalias = buscar_anomalias_contratista(session, nit)
                    if anomalias:
                        print(f"      Anomalías detectadas:")
                        for tipo, datos in anomalias.items():
                            print(f"        • {tipo}: {datos}")

                    resultados[caso_id] = {"nit": nit, "info": info, "anomalias": anomalias}
                    break

            if not encontrado:
                print(f"   ⚠️  No encontrado en el grafo (posible nombre distinto o datos anteriores a SECOP II)")
                resultados[caso_id] = {"encontrado": False}

        # --- Casos por entidad ---
        for caso_id, caso in CASOS.items():
            if "nit_entidad" not in caso:
                continue

            print(f"\n📋 {caso_id.upper()}")
            print(f"   {caso['desc']}")

            info_e = buscar_entidad(session, caso["nit_entidad"])
            if info_e and info_e.get("total_contratos", 0) > 0:
                valor_b = (info_e["valor_total"] or 0) / 1e9
                print(f"   ✅ ENTIDAD ENCONTRADA — NIT: {caso['nit_entidad']}")
                print(f"      Nombre: {info_e.get('nombre') or '(sin nombre)'}")
                print(f"      Contratos firmados: {info_e['total_contratos']:,} | Valor: ${valor_b:,.1f}B")

                top_c = buscar_contratistas_entidad(session, caso["nit_entidad"], top=5)
                if top_c:
                    print(f"      Top contratistas:")
                    for c in top_c:
                        val = (c["valor"] or 0) / 1e6
                        print(f"        {c['nit_c']} {c['nombre'] or ''} — {c['contratos']} contratos / ${val:,.0f}M")

                resultados[caso_id] = {"nit": caso["nit_entidad"], "info": info_e}
            else:
                print(f"   ⚠️  Entidad no encontrada (NIT: {caso['nit_entidad']})")
                resultados[caso_id] = {"encontrado": False}

    # Guardar resultados
    out = Path("/home/apolo/A/CorupCol/reports/calibracion_casos_conocidos.json")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n\nResultados guardados en: {out}")
    driver.close()


if __name__ == "__main__":
    main()
