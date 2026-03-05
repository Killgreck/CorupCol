import os
from grafo.config import DATA_DIR
from grafo.loaders.base_loader import load_csv_in_batches

def load_entidades():
    filepath = os.path.join(DATA_DIR, 'entidades.csv')
    
    query = """
    UNWIND $batch AS row
    
    MERGE (e:Entidad {nit: row.nit})
    ON CREATE SET 
        e.nombre = row.nombre,
        e.departamento = row.departamento,
        e.ciudad = coalesce(row.ciudad, "No Definida"),
        e.sector = row.sector,
        e.orden = coalesce(row.orden, "No Definido")

    WITH e, row
    WHERE row.departamento IS NOT NULL AND row.departamento <> ''

    MERGE (d:Departamento {nombre: toUpper(row.departamento)})
    MERGE (e)-[:UBICADA_EN]->(d)
    """
    
    return load_csv_in_batches(filepath, query, batch_size=1000, desc="Entidades")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    load_entidades()
