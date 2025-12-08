"""
Ouroboros - Schema Initialization Script
Initializes Neo4j database with provenance-aware schema and constraints.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from datetime import datetime

load_dotenv()


class SchemaInitializer:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "ouroboros123")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def create_constraints(self):
        """Create uniqueness constraints for node identifiers."""
        constraints = [
            # File nodes must have unique paths
            "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            
            # Class nodes must have unique fully qualified names
            "CREATE CONSTRAINT class_fqn_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.fully_qualified_name IS UNIQUE",
            
            # Function nodes must have unique signatures
            "CREATE CONSTRAINT function_signature_unique IF NOT EXISTS FOR (fn:Function) REQUIRE fn.signature IS UNIQUE",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"✓ Created constraint: {constraint.split('FOR')[1].split('REQUIRE')[0].strip()}")
                except Exception as e:
                    print(f"⚠ Constraint already exists or error: {e}")

    def create_indexes(self):
        """Create indexes for faster provenance and content lookups."""
        indexes = [
            # Provenance metadata indexes
            "CREATE INDEX provenance_model_name IF NOT EXISTS FOR (n:File) ON (n.model_name)",
            "CREATE INDEX provenance_timestamp IF NOT EXISTS FOR (n:File) ON (n.timestamp)",
            "CREATE INDEX provenance_checksum IF NOT EXISTS FOR (n:File) ON (n.context_checksum)",
            
            # Content search indexes
            "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX function_name IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
        ]

        with self.driver.session() as session:
            for index in indexes:
                try:
                    session.run(index)
                    print(f"✓ Created index: {index.split('FOR')[1].split('ON')[0].strip()}")
                except Exception as e:
                    print(f"⚠ Index already exists or error: {e}")

    def initialize_metadata(self):
        """Create the root metadata node for the Ouroboros system."""
        query = """
        MERGE (meta:SystemMetadata {system: 'ouroboros'})
        SET meta.version = $version,
            meta.initialized_at = $timestamp,
            meta.phase = 'Phase 1: The Librarian'
        RETURN meta
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                version=os.getenv("MODEL_VERSION", "1.0.0"),
                timestamp=datetime.utcnow().isoformat()
            )
            print(f"✓ Initialized system metadata: {result.single()['meta']}")

    def verify_connection(self):
        """Verify Neo4j connection is working."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 'Connection Successful' AS message")
                message = result.single()["message"]
                print(f"✓ Neo4j connection verified: {message}")
                return True
        except Exception as e:
            print(f"✗ Neo4j connection failed: {e}")
            return False


def main():
    print("=" * 60)
    print("Ouroboros - Phase 1: The Librarian")
    print("Schema Initialization")
    print("=" * 60)
    print()

    initializer = SchemaInitializer()

    # Step 1: Verify connection
    print("[Step 1/4] Verifying Neo4j connection...")
    if not initializer.verify_connection():
        print("\n✗ Failed to connect to Neo4j. Please ensure Docker container is running.")
        print("  Run: docker-compose up -d")
        return

    # Step 2: Create constraints
    print("\n[Step 2/4] Creating uniqueness constraints...")
    initializer.create_constraints()

    # Step 3: Create indexes
    print("\n[Step 3/4] Creating performance indexes...")
    initializer.create_indexes()

    # Step 4: Initialize metadata
    print("\n[Step 4/4] Initializing system metadata...")
    initializer.initialize_metadata()

    initializer.close()

    print("\n" + "=" * 60)
    print("✓ Schema initialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run: python scripts/ingest.py --path <your-project>")
    print("  2. Access Neo4j Browser: http://localhost:7474")
    print(f"  3. Login: {os.getenv('NEO4J_USER')} / {os.getenv('NEO4J_PASSWORD')}")


if __name__ == "__main__":
    main()
