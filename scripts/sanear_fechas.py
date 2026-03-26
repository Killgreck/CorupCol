#!/usr/bin/env python3
"""
Sanea fechas absurdas en anomalias_con_fechas.json (typos del SECOP).
Regla:
  - año > 2040 y (año - 100) en [1990, 2035] → corregir restando 100
  - año > 2040 sin corrección obvia → None
No re-escanea los CSVs (ya está hecho).
"""
import json
from pathlib import Path

ENTRADA = Path("reports/anomalias_con_fechas.json")

with open(ENTRADA, encoding="utf-8") as f:
    reporte = json.load(f)

def sanear(fecha_str):
    if not fecha_str:
        return None
    try:
        y = int(fecha_str[:4])
    except ValueError:
        return fecha_str
    if y > 2040:
        corrected = y - 100
        if 1990 <= corrected <= 2035:
            return str(corrected) + fecha_str[4:]
        return None   # placeholder sin corrección obvia
    return fecha_str

total = 0
saneadas = 0
nulleadas = 0

for cat, items in reporte["anomalias"].items():
    for r in items:
        total += 1
        for campo in ("fecha_inicio", "fecha_fin", "fecha"):
            original = r.get(campo)
            if original:
                nuevo = sanear(original)
                if nuevo != original:
                    r[campo] = nuevo
                    if nuevo is None:
                        nulleadas += 1
                    else:
                        saneadas += 1

with open(ENTRADA, "w", encoding="utf-8") as f:
    json.dump(reporte, f, ensure_ascii=False)

print(f"Procesados: {total} registros")
print(f"  Corregidos (typo -100 años): {saneadas}")
print(f"  Nulleados (sin corrección obvia): {nulleadas}")

# Verificar que no quedan fechas raras
restantes = []
for cat, items in reporte["anomalias"].items():
    for r in items:
        for campo in ("fecha_inicio", "fecha_fin"):
            v = r.get(campo)
            if v and int(v[:4]) > 2035:
                restantes.append(f"{v} [{cat[:20]}]")

if restantes:
    print(f"\nAún quedan {len(restantes)} fechas > 2035:")
    for x in restantes[:10]:
        print(f"  {x}")
else:
    print("\nOK — no quedan fechas > 2035")
