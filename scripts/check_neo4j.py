
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "ouroboros123")

passwords_to_try = [password, "password", "neo4j", "12345678", "admin"]

for p in passwords_to_try:
    print(f"Trying password: {p}")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, p))
        driver.verify_connectivity()
        print(f"Neo4j: SUCCESS with password '{p}'")
        driver.close()
        break
    except Exception as e:
        print(f"Neo4j: FAIL with '{p}' - {e}")
