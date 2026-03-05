import argparse
import logging
import sys
from datetime import datetime
from grafo.schema import setup_schema
from grafo.loaders.entidades import load_entidades
from grafo.loaders.contratistas import load_contratistas
from grafo.loaders.contratos import load_all_contratos
from grafo.loaders.procesos import load_procesos
from grafo.loaders.bpin import load_bpin
from grafo.reporte import generar_reporte
from grafo.config import db

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MAIN")

def execute_load():
    logger.info("Iniciando proceso de carga hacia Neo4j...")
    try:
        setup_schema()
        load_entidades()
        load_contratistas()
        load_all_contratos()
        load_procesos()
        load_bpin()
        logger.info("Carga de todos los datasets finalizada con éxito.")
    except Exception as e:
        logger.error(f"Error durante la carga de datos: {e}")
        sys.exit(1)

def execute_analyze():
    logger.info("Iniciando análisis de grafos y detección de anomalías...")
    try:
        report_path = generar_reporte()
        logger.info(f"Análisis finalizado.")
    except Exception as e:
        logger.error(f"Error durante el análisis: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Pipeline ETL y Análisis para el Grafo Neo4j de Contratación Colombia")
    parser.add_argument("--load", action="store_true", help="Importa todos los CSVs al grafo Neo4j")
    parser.add_argument("--analyze", action="store_true", help="Corre las 6 queries de anomalías y genera el reporte JSON")
    parser.add_argument("--all", action="store_true", help="Ejecuta tanto --load como --analyze secuencialmente")
    
    args = parser.parse_args()
    
    if args.all:
        execute_load()
        execute_analyze()
    elif args.load:
        execute_load()
    elif args.analyze:
        execute_analyze()
    else:
        parser.print_help()
        
    # Cerramos el pool de driver
    db.close()

if __name__ == "__main__":
    main()
