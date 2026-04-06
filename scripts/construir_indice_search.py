"""
construir_indice_search.py
--------------------------
Construye la base de datos SQLite con índice FTS5 para el buscador
del dashboard. Lee TODOS los chunks de secop_integrado (SECOP I + II).

Salida: instance/search.db
Tiempo estimado: 15-45 minutos dependiendo del hardware.
Ejecutar una sola vez, o cuando lleguen nuevos datos.

Uso:
    python3 scripts/construir_indice_search.py
    python3 scripts/construir_indice_search.py --solo-recientes  # solo 2020-2026
"""
import gzip, csv, sqlite3, sys, os, time
from pathlib import Path

BASE     = Path(__file__).parent.parent
CHUNKS   = BASE / 'data' / 'secop_integrado'
DB_PATH  = BASE / 'instance' / 'search.db'

# Filtro opcional para solo años recientes
SOLO_RECIENTES = '--solo-recientes' in sys.argv
AÑO_MINIMO    = '2020' if SOLO_RECIENTES else '2000'

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-65536;  -- 64 MB cache

CREATE TABLE IF NOT EXISTS contratos (
    id             INTEGER PRIMARY KEY,
    objeto         TEXT,
    entidad        TEXT,
    nit_entidad    TEXT,
    contratista    TEXT,
    doc_contratista TEXT,
    valor          REAL,
    fecha          TEXT,
    estado         TEXT,
    depto          TEXT,
    ciudad         TEXT,
    url            TEXT,
    fuente         TEXT,
    numero         TEXT
);

CREATE INDEX IF NOT EXISTS idx_doc     ON contratos(doc_contratista);
CREATE INDEX IF NOT EXISTS idx_fecha   ON contratos(fecha);
CREATE INDEX IF NOT EXISTS idx_entidad ON contratos(nit_entidad);

CREATE VIRTUAL TABLE IF NOT EXISTS contratos_fts USING fts5(
    objeto,
    entidad,
    contratista,
    content='contratos',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
"""

TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS contratos_ai AFTER INSERT ON contratos BEGIN
    INSERT INTO contratos_fts(rowid, objeto, entidad, contratista)
    VALUES (new.id, new.objeto, new.entidad, new.contratista);
END;
"""

def parse_valor(s):
    if not s:
        return 0.0
    try:
        return float(str(s).replace(',', '').replace(' ', '') or 0)
    except ValueError:
        return 0.0

def parse_row(row):
    fecha = (row.get('fecha_de_firma_del_contrato') or '')[:10]
    if SOLO_RECIENTES and fecha[:4] < AÑO_MINIMO:
        return None

    return (
        (row.get('objeto_a_contratar') or row.get('objeto_del_proceso') or '')[:500].strip(),
        (row.get('nombre_de_la_entidad') or '')[:200].strip(),
        (row.get('nit_de_la_entidad') or '').strip(),
        (row.get('nom_raz_social_contratista') or '')[:200].strip(),
        (row.get('documento_proveedor') or '').strip(),
        parse_valor(row.get('valor_contrato')),
        fecha,
        (row.get('estado_del_proceso') or '').strip()[:50],
        (row.get('departamento_entidad') or '').strip()[:100],
        (row.get('municipio_entidad') or '').strip()[:100],
        (row.get('url_contrato') or '').strip()[:300],
        (row.get('origen') or 'SECOP').strip()[:10],
        (row.get('numero_del_contrato') or '').strip()[:80],
    )

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    chunks = sorted(CHUNKS.glob('chunk_*.csv.gz'))
    total_chunks = len(chunks)

    if not chunks:
        print(f"ERROR: No se encontraron chunks en {CHUNKS}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"  Construyendo índice de búsqueda SECOP")
    print(f"  Chunks a procesar: {total_chunks}")
    print(f"  Filtro años: desde {AÑO_MINIMO}")
    print(f"  Destino: {DB_PATH}")
    print(f"{'='*60}")

    # Si existe, preguntar si sobrescribir
    if DB_PATH.exists():
        answer = input(f"\nYa existe {DB_PATH}. ¿Sobrescribir? [s/N]: ").strip().lower()
        if answer != 's':
            print("Cancelado.")
            sys.exit(0)
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)
    conn.executescript(TRIGGERS)
    conn.commit()

    insert_sql = """
        INSERT INTO contratos
            (objeto, entidad, nit_entidad, contratista, doc_contratista,
             valor, fecha, estado, depto, ciudad, url, fuente, numero)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    total_filas = 0
    t0 = time.time()
    BATCH = 5000

    for i, chunk in enumerate(chunks, 1):
        t1 = time.time()
        batch = []
        try:
            with gzip.open(chunk, 'rt', encoding='utf-8', errors='replace') as fp:
                for row in csv.DictReader(fp):
                    parsed = parse_row(row)
                    if parsed:
                        batch.append(parsed)
                    if len(batch) >= BATCH:
                        conn.executemany(insert_sql, batch)
                        total_filas += len(batch)
                        batch = []

            if batch:
                conn.executemany(insert_sql, batch)
                total_filas += len(batch)
            conn.commit()

        except Exception as e:
            print(f"\n  WARN: error en {chunk.name}: {e}", file=sys.stderr)
            continue

        elapsed = time.time() - t0
        rate    = total_filas / elapsed if elapsed > 0 else 0
        eta     = (total_chunks - i) * (elapsed / i) if i > 0 else 0
        print(f"\r  [{i:4d}/{total_chunks}] {total_filas:,} filas  {rate:,.0f}/s  ETA {eta/60:.1f} min    ",
              end='', flush=True)

    print(f"\n\nOptimizando FTS5...")
    conn.execute("INSERT INTO contratos_fts(contratos_fts) VALUES('optimize')")
    conn.execute("ANALYZE")
    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    size_mb = DB_PATH.stat().st_size / 1e6
    print(f"\n{'='*60}")
    print(f"  Filas insertadas : {total_filas:,}")
    print(f"  Tiempo total     : {elapsed/60:.1f} min")
    print(f"  Tamaño DB        : {size_mb:.0f} MB")
    print(f"  Listo: {DB_PATH}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
