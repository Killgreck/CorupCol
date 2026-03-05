import os
from grafo.config import DATA_DIR
from grafo.loaders.base_loader import load_csv_in_batches

def load_contratistas():
    filepath = os.path.join(DATA_DIR, 'contratistas.csv')
    
    query = """
    UNWIND $batch AS row
    
    MERGE (c:Contratista {doc_id: row.doc_id})
    ON CREATE SET 
        c.nombre = row.nombre,
        c.tipo_doc = row.tipo_doc,
        c.es_pyme = row.es_pyme,
        c.nacionalidad = row.nacionalidad
    
    WITH c, row
    WHERE row.rep_legal IS NOT NULL AND row.rep_legal <> ''
    
    MERGE (p:Persona {doc_id: row.rep_legal_doc_id})
    ON CREATE SET
        p.nombre = row.rep_legal,
        p.rol = 'rep_legal'

    MERGE (p)-[:ES_REP_LEGAL_DE]->(c)
    """
    
    # We might need to handle OPERA_EN if there's a department field in contratistas.
    # The prompt explicitly lists doc_id, nombre, rep_legal for Contratistas.csv
    # So we handle what is possible. If they operate in a department, we need that info.
    # We assume if 'depto' is in row we link it.
    
    query_with_depto = """
    UNWIND $batch AS row
    
    MERGE (c:Contratista {doc_id: row.doc_id})
    ON CREATE SET 
        c.nombre = row.nombre,
        c.tipo_doc = coalesce(row.tipo_doc, 'Desconocido'),
        c.es_pyme = coalesce(row.es_pyme, 'No'),
        c.nacionalidad = coalesce(row.nacionalidad, 'Desconocida')
        
    WITH c, row
    
    // Si hay depto, crear relación OPERA_EN
    FOREACH (depto_name IN CASE WHEN row.departamento IS NOT NULL AND row.departamento <> '' THEN [row.departamento] ELSE [] END |
        MERGE (d:Departamento {nombre: toUpper(depto_name)})
        MERGE (c)-[:OPERA_EN]->(d)
    )
    
    WITH c, row
    // Asumiendo que pueden venir datos de representante legal si es empresa
    FOREACH (doc IN CASE WHEN row.id_rep_legal IS NOT NULL AND row.id_rep_legal <> '' THEN [row.id_rep_legal] ELSE [] END |
        MERGE (p:Persona {doc_id: doc})
        ON CREATE SET
            p.nombre = coalesce(row.rep_legal, 'Desconocido'),
            p.rol = 'rep_legal'
        MERGE (p)-[:ES_REP_LEGAL_DE]->(c)
    )
    """

    # Replace with the robust query that handles optional fields gracefully since CSVs can be messy
    return load_csv_in_batches(filepath, query_with_depto, batch_size=1000, desc="Contratistas")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    load_contratistas()
