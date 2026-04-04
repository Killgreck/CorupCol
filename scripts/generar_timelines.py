import json
import os
import sys

# Agregar el directorio principal al path para poder importar grafo.config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from grafo.config import db

DASHBOARD_DIR = os.path.join(parent_dir, "dashboard", "data")
CARRUSEL_FILE = os.path.join(DASHBOARD_DIR, "carrusel.json")
NEPOTISMO_FILE = os.path.join(DASHBOARD_DIR, "nepotismo.json")
OUTPUT_FILE = os.path.join(DASHBOARD_DIR, "timelines.json")

def to_billions(value):
    if not isinstance(value, (int, float)):
        return 0.0
    return round(value / 1_000_000_000, 2)  # Millions or Billions? El dashboard usa "billones" (1e12 COP) pero a veces millones. Let's do COP value raw or Millions to be safe. We'll send raw value and let JS format it.

def main():
    print(f"Cargando {CARRUSEL_FILE}...")
    try:
        with open(CARRUSEL_FILE, "r", encoding="utf-8") as f:
            carrusel_data = json.load(f)
    except FileNotFoundError:
        print("No se encontró carrusel.json")
        return

    try:
        with open(NEPOTISMO_FILE, "r", encoding="utf-8") as f:
            nepotismo_data = json.load(f)
    except FileNotFoundError:
        print("No se encontró nepotismo.json")
        nepotismo_data = []

    nits = [item["c.doc_id"] for item in carrusel_data if "c.doc_id" in item]
    nits_nepotismo = [item["p.doc_id"] for item in nepotismo_data if "p.doc_id" in item]
    
    if not nits and not nits_nepotismo:
        print("No se encontraron NITs ni CCs válidos")
        return
        
    print(f"Buscando timelines para {len(nits)} contratistas y {len(nits_nepotismo)} ordenadores...")

    query = """
    UNWIND $nits AS target_nit
    MATCH (c:Contratista {doc_id: target_nit})-[:GANÓ]->(ct:Contrato)
    RETURN c.doc_id AS nit, ct.fecha_firma AS fecha, ct.valor AS valor, ct.id AS contrato_id
    ORDER BY fecha
    """

    driver = db.get_driver()
    timelines = {}
    
    with driver.session() as session:
        print("Asegurando índice en doc_id de Contratista...")
        session.run("CREATE INDEX contratista_doc_id_idx IF NOT EXISTS FOR (c:Contratista) ON (c.doc_id)")
        
        print(f"Ejecutando query...")
        result = session.run(query, nits=nits)
        for record in result:
            nit = record["nit"]
            fecha = record["fecha"]
            valor = record["valor"]
            # Convert date to string if it's a date object
            if hasattr(fecha, 'isoformat'):
                fecha = fecha.isoformat()
            
            # Format fecha to just YYYY-MM
            if fecha and len(str(fecha)) >= 7:
                mes_str = str(fecha)[:7]
            else:
                mes_str = "Desconocido"

            if nit not in timelines:
                timelines[nit] = []
                
            timelines[nit].append({
                "fecha": mes_str,
                "valor": valor or 0,
                "contrato_id": record["contrato_id"]
            })

        # --- SEGUNDA FASE: NEPOTISMO ---
        if nits_nepotismo:
            print("Asegurando índice en doc_id de Persona...")
            session.run("CREATE INDEX persona_doc_id_idx IF NOT EXISTS FOR (p:Persona) ON (p.doc_id)")
            
            query_nepotismo = """
            UNWIND $nits AS target_doc_id
            MATCH (p:Persona {doc_id: target_doc_id})-[:ORDENÓ]->(ct:Contrato)
            RETURN p.doc_id AS nit, ct.fecha_firma AS fecha, ct.valor AS valor, ct.id AS contrato_id
            ORDER BY fecha
            """
            print(f"Ejecutando query de nepotismo...")
            result_nep = session.run(query_nepotismo, nits=nits_nepotismo)
            for record in result_nep:
                nit = record["nit"]
                fecha = record["fecha"]
                valor = record["valor"]
                if hasattr(fecha, 'isoformat'):
                    fecha = fecha.isoformat()
                
                if fecha and len(str(fecha)) >= 7:
                    mes_str = str(fecha)[:7]
                else:
                    mes_str = "Desconocido"

                if nit not in timelines:
                    timelines[nit] = []
                    
                timelines[nit].append({
                    "fecha": mes_str,
                    "valor": valor or 0,
                    "contrato_id": record["contrato_id"]
                })

    # Ahora agregamos los datos por mes/año
    aggregated_timelines = {}
    for nit, records in timelines.items():
        # Agrupar por mes o año. Vamos a agrupar por año-mes.
        grouped = {}
        for r in records:
            mes = r["fecha"] if r["fecha"] != "Desconocido" else "Sin Fecha"
            val_b = (r["valor"] / 1_000_000_000_000)  # Convert to billones for display? No, better keep it as is or Billions. Let's send Billions to match UI.
            if mes not in grouped:
                grouped[mes] = {"valor_total_b": 0, "num_contratos": 0}
            grouped[mes]["valor_total_b"] += val_b
            grouped[mes]["num_contratos"] += 1
            
        # Convert to sorted list con "Sin Fecha" al comienzo
        sorted_keys = sorted([k for k in grouped.keys() if k != "Sin Fecha"])
        final_list = []
        
        if "Sin Fecha" in grouped:
            final_list.append({
                "fecha": "Sin Fecha",
                "valor_total_b": round(grouped["Sin Fecha"]["valor_total_b"], 4),
                "num_contratos": grouped["Sin Fecha"]["num_contratos"]
            })
            
        for k in sorted_keys:
            final_list.append({
                "fecha": k,
                "valor_total_b": round(grouped[k]["valor_total_b"], 4),
                "num_contratos": grouped[k]["num_contratos"]
            })
            
        aggregated_timelines[nit] = final_list

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(aggregated_timelines, f, indent=2, ensure_ascii=False)
        
    print(f"Éxito: Timelines exportados a {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
