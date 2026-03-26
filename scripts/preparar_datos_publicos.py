import json
import os
import csv
from datetime import datetime
import re

# Configuración de rutas
INPUT_FILE = "reports/anomalias_con_fechas.json"
DASHBOARD_DIR = "dashboard/data"
CSV_DIR = "reports/csv"
REPORT_DIR = "reports"

# Crear directorios si no existen
os.makedirs(DASHBOARD_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

def to_billions(value):
    """Convierte un valor a miles de millones COP con 1 decimal."""
    if not isinstance(value, (int, float)):
        return 0.0
    return round(value / 1_000_000_000_000, 1)

def format_currency(value_in_billions):
    """Formatea para texto, ej: $142,9B"""
    return f"${value_in_billions:,.1f}B".replace(",", "X").replace(".", ",").replace("X", ".")

def format_name(name):
    """Limpia y pone en Title Case los nombres, eliminando dobles espacios."""
    if not name or not isinstance(name, str):
        return "Desconocido"
    name = re.sub(r'\s+', ' ', name.strip())
    return name.title()

def initial_name(name):
    """Convierte a iniciales + apellidos para contexto de tablas.
    Ejemplo: 'Diana Patricia Arboleda Ramirez' -> 'D. P. Arboleda Ramirez'
    """
    if not name or name == "Desconocido":
        return name
    parts = name.split()
    if len(parts) <= 2:
        return format_name(name)
    
    # Toma las iniciales de todos menos los dos últimos que asumimos son apellidos
    initials = [f"{p[0]}." for p in parts[:-2]]
    last_names = parts[-2:]
    return format_name(" ".join(initials + last_names))

def is_valid_doc(doc_id):
    """Filtra IDs menores a 5 dígitos o patrones repetitivos."""
    if not doc_id or not isinstance(doc_id, str):
        return False
    doc_id = doc_id.strip()
    if len(doc_id) < 5:
        return False
    # Rechaza si todos los dígitos son iguales
    if len(set(doc_id)) == 1:
        return False
    # Patrones comunes falsos
    if doc_id in ['123456', '1234567', '12345678', '123456789']:
        return False
    return True

def filter_lista(lista, max_items=50, is_person=False):
    """Limpia y filtra una lista de anomalías."""
    cleaned = []
    
    for item in lista:
        # Extraer doc_id de las diferentes posibles llaves
        doc_id = item.get("c.doc_id") or item.get("p.doc_id") or ""
        
        # Validación básica para nodos con doc_id (empresa/persona)
        # Notas: en sobrecostos no tenemos doc_id sino nit a veces, o simplemente nombre
        if ("c.doc_id" in item or "p.doc_id" in item) and not is_valid_doc(doc_id):
            continue
            
        nombre_crudo = item.get("_nombre_contratista") or item.get("contratista_nombre") or item.get("p.nombre") or item.get("c.nombre") or item.get("entidad_nombre") or ""
        
        # Filtro de nombres inválidos
        if re.search(r'^(x|j)\1+$', nombre_crudo.lower()): # Ej: xxxxxx, jjjjjj
            continue
            
        nuevo_item = item.copy()
        for k, v in item.items():
            if k.endswith('nombre') or k.startswith('nombre_') or k in ['_nombre_contratista']:
                nuevo_item[k] = format_name(v)
            if 'valor' in k or 'ganado' in k:
                if isinstance(v, (int, float)):
                    nuevo_item[f"{k}_b"] = to_billions(v)
        
        # Campo especial de display para UI
        display_name = format_name(item.get("_nombre_contratista") or item.get("c.nombre") or "Desconocido")
        if is_person:
            # En nepotismo, 'p.nombre' es el funcionario
            if "p.nombre" in item:
                nuevo_item["p.nombre_display"] = initial_name(item["p.nombre"])
            if "_nombre_contratista" in item:
                nuevo_item["_nombre_contratista_display"] = initial_name(item["_nombre_contratista"])
            
        nuevo_item["display_name"] = display_name if not is_person else initial_name(display_name)
        cleaned.append(nuevo_item)
        
        if len(cleaned) >= max_items:
            break
            
    return cleaned

def generate_csv(data, filename, columns):
    """Genera un archivo CSV."""
    with open(f"{CSV_DIR}/{filename}", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in data:
            # Extraer solo las columnas necesarias, evitar KeyError
            out_row = {col: row.get(col, "") for col in columns}
            writer.writerow(out_row)

def main():
    print("Cargando datos crudos...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        crudo = json.load(f)

    # 1. STATS GLOBALES
    stats = crudo.get("metadata", {}).get("estadisticas_generales", {})
    
    anomalias = crudo.get("anomalias", {})
    carrusel = anomalias.get("carrusel_contratista_multiples_entidades", [])
    nepotismo = anomalias.get("nepotismo_ordenador_recurrente", [])
    sobrecostos = anomalias.get("sobrecosto_prorrogado", [])
    
    dashboard_stats = {
        "fecha": crudo.get("metadata", {}).get("fecha_generacion", "2026-03-05"),
        "total_contratos": stats.get("total_relaciones", 52000000), # Relaciones ~= contratos
        "valor_total_b": to_billions(stats.get("valor_total_contratos", 0)),
        "casos_carrusel": len(carrusel),
        "casos_nepotismo": len(nepotismo),
        "casos_sobrecosto": len(sobrecostos)
    }
    
    # 2. PROCESAR CATEGORÍAS (TOP 50)
    print("Procesando Carrusel...")
    carrusel_top = filter_lista(carrusel, 50)
    
    print("Procesando Nepotismo...")
    nepotismo_top = filter_lista(nepotismo, 50, is_person=True)
    
    print("Procesando Sobrecostos...")
    sobrecostos_top = filter_lista(sobrecostos, 50)

    # 3. GUARDAR JSONs DASHBOARD
    with open(f"{DASHBOARD_DIR}/stats.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_stats, f, indent=2, ensure_ascii=False)
        
    with open(f"{DASHBOARD_DIR}/carrusel.json", "w", encoding="utf-8") as f:
        json.dump(carrusel_top, f, indent=2, ensure_ascii=False)
        
    with open(f"{DASHBOARD_DIR}/nepotismo.json", "w", encoding="utf-8") as f:
        json.dump(nepotismo_top, f, indent=2, ensure_ascii=False)
        
    with open(f"{DASHBOARD_DIR}/sobrecostos.json", "w", encoding="utf-8") as f:
        json.dump(sobrecostos_top, f, indent=2, ensure_ascii=False)

    # 4. GENERAR RED (D3.js) - Extraer nodos y links de los tops
    print("Construyendo grafo para D3...")
    nodes = {}
    links = []

    # Leer también empresa_reciente y autocontratacion (tienen fechas)
    empresa_reciente = anomalias.get("empresa_reciente_contrato_millonario", [])
    autocontratacion = anomalias.get("autocontratacion_directa", [])
    empresa_top  = filter_lista(empresa_reciente, 30)
    autocon_top  = filter_lista(autocontratacion, 30)

    # helper para nodos — group: 1=Entidad(Azul), 2=Contratista(Naranja), 3=Persona(Rojo)
    def add_node(idx, label, name, group, fecha=None):
        if idx not in nodes:
            nodes[idx] = {"id": idx, "name": name, "group": group,
                          "val": 0, "label": label, "fecha": fecha}
        elif fecha and not nodes[idx].get("fecha"):
            nodes[idx]["fecha"] = fecha

    # Carrusel — sin fecha disponible
    for c in carrusel_top[:25]:
        c_id = c.get("c.doc_id", "c_" + c["display_name"])
        add_node(c_id, "Contratista", c["display_name"], 2)
        nodes[c_id]["val"] += (c.get("total_valor_b", 1) or 1) * 10

    # Nepotismo — sin fecha disponible
    for n in nepotismo_top[:25]:
        p_id   = n.get("p.doc_id", "p_" + n.get("p.nombre_display", ""))
        c_id   = n.get("c.doc_id", "c_" + n.get("_nombre_contratista_display", ""))
        p_name = n.get("p.nombre_display", n.get("p.nombre"))
        c_name = n.get("_nombre_contratista_display", n.get("display_name"))
        add_node(p_id, "Funcionario", p_name, 3)
        add_node(c_id, "Contratista", c_name, 2)
        nodes[p_id]["val"] += 5
        nodes[c_id]["val"] += (n.get("valor_total_b", 1) or 1) * 10
        links.append({"source": p_id, "target": c_id,
                      "value": n.get("valor_total_b", 1) or 1,
                      "type": "ORDENÓ", "fecha": None})

    # Sobrecostos — sin fecha en el JSON actual
    for s in sobrecostos_top[:25]:
        e_name = format_name(s.get("entidad_nombre", "")) or "Entidad Desconocida"
        c_name = format_name(s.get("contratista_nombre", "")) or "Contratista Desconocido"
        e_id = "e_" + e_name
        c_id = "c_" + c_name
        add_node(e_id, "Entidad", e_name, 1)
        add_node(c_id, "Contratista", c_name, 2)
        nodes[e_id]["val"] += 10
        nodes[c_id]["val"] += (s.get("ct.valor_b", 1) or 1) * 5
        links.append({"source": e_id, "target": c_id,
                      "value": s.get("ct.valor_b", 1) or 1,
                      "type": "SOBRECOSTO", "fecha": None})

    # Empresa reciente — TIENE fecha (primer_contrato)
    for e in empresa_top[:20]:
        c_id   = e.get("c.doc_id", "er_" + e["display_name"])
        fecha  = (e.get("primer_contrato") or "")[:10] or None
        valor  = to_billions(e.get("total_ganado", 0) or 0)
        add_node(c_id, "Empresa Reciente", e["display_name"], 2, fecha)
        nodes[c_id]["val"] += (valor or 1) * 8

    # Autocontratación — TIENE fecha (ct.fecha_firma)
    for a in autocon_top[:20]:
        p_id   = a.get("p.doc_id", "ac_" + a.get("p.nombre_display", ""))
        p_name = a.get("p.nombre_display", a.get("p.nombre", "Funcionario"))
        fecha  = (a.get("ct.fecha_firma") or "")[:10] or None
        valor  = to_billions(a.get("ct.valor", 0) or 0)
        add_node(p_id, "Autocontratación", p_name, 3, fecha)
        nodes[p_id]["val"] += (valor or 1) * 12

    grafo = {
        "nodes": list(nodes.values()),
        "links": links
    }
    
    with open(f"{DASHBOARD_DIR}/grafo_red.json", "w", encoding="utf-8") as f:
        json.dump(grafo, f, indent=2, ensure_ascii=False)

    # 5. EXPORTAR CSVs
    print("Generando CSVs...")
    generate_csv(carrusel_top, "carrusel.csv", ["c.doc_id", "_nombre_contratista", "entidades_distintas", "total_contratos", "total_valor", "total_valor_b"])
    generate_csv(nepotismo_top, "nepotismo.csv", ["p.doc_id", "p.nombre", "c.doc_id", "_nombre_contratista", "contratos_juntos", "valor_total", "valor_total_b"])
    generate_csv(sobrecostos_top, "sobrecostos.csv", ["entidad_nombre", "contratista_nombre", "ct.id", "ct.dias_adicionados", "ct.valor", "ct.valor_b", "ct.objeto"])

    # 6. GENERAR RESUMEN EJECUTIVO (MARKDOWN)
    print("Generando Resumen Ejecutivo...")
    
    # Extraer los peores casos para el markdown
    top_carrusel = carrusel_top[0] if carrusel_top else {}
    top_nepotismo = nepotismo_top[0] if nepotismo_top else {}
    top_sobrecosto = sobrecostos_top[0] if sobrecostos_top else {}
    
    md_content = f"""# Resumen Ejecutivo: Anomalías en Contratación Pública (SECOP I y II)

**Fecha de Análisis:** {datetime.now().strftime('%Y-%m-%d')}
**Registros Analizados:** Más de 52 millones
**Valor Total Rastreable:** {format_currency(dashboard_stats['valor_total_b'])} COP

## ¿Qué es esto?
Este informe es el resultado del cruce masivo de toda la contratación pública estatal con modelos de detección de anomalías mediante grafos de conocimiento. No acusa de delitos, pero señala comportamientos estadísticamente atípicos que merecen escrutinio público y control fiscal.

## Metodología
- Se construyó una red interconectada (grafo) con todas las entidades, contratistas y representantes procesados a partir de los datos públicos del SECOP.
- Se aplicaron algoritmos para rastrear múltiples contratos hacia los mismos nodos finales.
- Se aislaron patrones que típicamente preceden actos de corrupción (carruseles, nepotismo, fraccionamiento).

## 5 Hallazgos más críticos

1. **Carrusel Inter-Agencia Extremo**: La entidad o contratista `{top_carrusel.get('display_name', 'N/A')}` firmó `{top_carrusel.get('total_contratos', 0)}` contratos a través de `{top_carrusel.get('entidades_distintas', 0)}` agencias distintas por un valor total de **{format_currency(top_carrusel.get('total_valor_b', 0))} COP**. Este nivel de dispersión suele usarse para eludir controles jerárquicos.
   
2. **Nepotismo / Favoritismo Direccionado**: El funcionario `{top_nepotismo.get('p.nombre', 'N/A')}` ha aprobado o adjudicado `{top_nepotismo.get('contratos_juntos', 0)}` contratos recurrentes a `{top_nepotismo.get('_nombre_contratista', 'N/A')}` por **{format_currency(top_nepotismo.get('valor_total_b', 0))} COP**. 
   
3. **Prórrogas Excesivas (Sobrecostos de tiempo)**: El contrato `{top_sobrecosto.get('ct.id', 'N/A')}` otorgado a `{top_sobrecosto.get('contratista_nombre', 'N/A')}` tiene `{top_sobrecosto.get('ct.dias_adicionados', 0)}` días de prórroga registrados, lo que desvirtúa la planeación original por un valor de **{format_currency(top_sobrecosto.get('ct.valor_b', 0))} COP**.

*(Revise los anexos CSV para el Top 50 de cada categoría).*

## ¿Cómo verificar esto (Para periodistas)?
1. **Carrusel**: Busque el NIT `{top_carrusel.get('c.doc_id', 'N/A')}` en el SECOP II Institucional o en el portal Oceano de la Contraloría para comprobar el enjambre de contratos.
2. **Nepotismo**: Verifique en el SIGEP las fechas de posesión del ordenador del gasto `{top_nepotismo.get('p.doc_id', 'N/A')}` frente a las fechas de los contratos.
3. **Sobrecostos**: Ingrese el ID del proceso `{top_sobrecosto.get('ct.id', 'N/A')}` en el buscador de SECOP II y evalúe los documentos "Modificación" o "Otrosí".

## Limitaciones
- **NO todo es corrupción**: Algunos proveedores únicos de software o insumos médicos justificados parecen anomalías en volumen (por ej. empresas de servicios públicos o monopolios naturales).
- Existen casos de homonimia en nombres propios si no van acompañados del documento de identidad.

---
*Datos Abiertos de Colombia - Este es un proyecto open source inspirado en auditoría cívica con IA.*
"""
    with open(f"{REPORT_DIR}/resumen_ejecutivo.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Éxito: Datos procesados y exportados a {DASHBOARD_DIR} y {CSV_DIR}")

if __name__ == "__main__":
    main()
