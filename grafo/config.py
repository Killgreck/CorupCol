import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables from .env file
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATA_DIR = os.getenv("DATA_DIR", "/home/apolo/A/CorupCol/normalized")

class Neo4jConnection:
    def __init__(self, uri, user, pwd):
        self._driver = GraphDatabase.driver(uri, auth=(user, pwd))

    def close(self):
        if self._driver is not None:
            self._driver.close()

    def get_driver(self):
        return self._driver

# Singleton-like instance for the rest of the app to use
db = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
