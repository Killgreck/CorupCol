"""
Genera archivos JSON de detalle de contratos por NIT contratista,
agrupados por período (YYYY-MM), para el feature de drill-down
en la línea de tiempo del dashboard.

Salida: dashboard/data/contratos/<nit>.json
  {
    "YYYY-MM": [
      {id_contrato, objeto, valor, fecha_firma, entidad, estado, tipo, url, ...},
      ...
    ],
    ...
  }
"""
import gzip, csv, json, os, sys
from pathlib import Path

BASE   = Path(__file__).parent.parent
DATA   = BASE / 'data' / 'secop2_contratos'
OUT    = BASE / 'dashboard' / 'data' / 'contratos'
TL     = BASE / 'dashboard' / 'data' / 'timelines.json'

CAMPOS = [
    'id_contrato', 'objeto_del_contrato', 'descripcion_del_proceso',
    'valor_del_contrato', 'fecha_de_firma', 'fecha_de_inicio_del_contrato',
    'fecha_de_fin_del_contrato', 'nombre_entidad', 'nit_entidad',
    'estado_contrato', 'tipo_de_contrato', 'modalidad_de_contratacion',
    'proveedor_adjudicado', 'documento_proveedor',
    'nombre_representante_legal', 'urlproceso',
    'dias_adicionados', 'duraci_n_del_contrato',
    'nombre_ordenador_del_gasto', 'ciudad', 'departamento',
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    with open(TL) as f:
        nits_objetivo = set(json.load(f).keys())

    print(f"NITs objetivo: {len(nits_objetivo)}")

    # Acumulador: nit -> periodo -> [contratos]
    acum = {nit: {} for nit in nits_objetivo}

    chunks = sorted(DATA.glob('chunk_*.csv.gz'))
    total  = len(chunks)
    encontrados = 0

    for i, chunk in enumerate(chunks, 1):
        print(f"\r  Procesando chunk {i}/{total}...", end='', flush=True)
        try:
            with gzip.open(chunk, 'rt', encoding='utf-8', errors='replace') as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    doc = (row.get('documento_proveedor') or '').strip()
                    if doc not in nits_objetivo:
                        continue
                    encontrados += 1
                    fecha = (row.get('fecha_de_firma') or '')[:7]  # YYYY-MM
                    if not fecha:
                        fecha = 'sin_fecha'
                    contrato = {k: (row.get(k) or '').strip() for k in CAMPOS if k in row}
                    # Normalizar valor
                    try:
                        contrato['valor_del_contrato'] = float(
                            contrato.get('valor_del_contrato', '0').replace(',', '').replace(' ', '') or 0
                        )
                    except ValueError:
                        contrato['valor_del_contrato'] = 0
                    acum[doc].setdefault(fecha, []).append(contrato)
        except Exception as e:
            print(f"\n  Error en {chunk.name}: {e}", file=sys.stderr)

    print(f"\nContratos encontrados: {encontrados}")

    for nit, periodos in acum.items():
        # Ordenar períodos cronológicamente, ordenar contratos por fecha dentro de cada período
        for periodo in periodos:
            periodos[periodo].sort(key=lambda c: c.get('fecha_de_firma', ''))
        ordered = dict(sorted(periodos.items()))
        out_file = OUT / f"{nit}.json"
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(ordered, f, ensure_ascii=False, separators=(',', ':'))
        n_contratos = sum(len(v) for v in ordered.values())
        print(f"  {nit}: {n_contratos} contratos en {len(ordered)} períodos → {out_file.name}")

    print("\nListo.")

if __name__ == '__main__':
    main()
