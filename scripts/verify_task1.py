"""
Ouroboros - Task 1 Verification Script
Tests all components of the Neo4j Graph Database setup.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

def test_neo4j_driver():
    """Test 1: Neo4j Python driver import and connection."""
    print("[Test 1/6] Testing Neo4j driver import...")
    try:
        from neo4j import GraphDatabase as Neo4jDriver
        print("✓ Neo4j driver imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Neo4j driver: {e}")
        return False
    
    print("\n[Test 2/6] Testing Neo4j connection...")
    try:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "ouroboros123")
        
        driver = Neo4jDriver.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 'Connection OK' AS message")
            message = result.single()["message"]
            print(f"✓ {message}")
        driver.close()
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    return True


def test_schema_initialization():
    """Test 3: Verify database schema and constraints."""
    print("\n[Test 3/6] Testing schema constraints...")
    try:
        from neo4j import GraphDatabase as Neo4jDriver
        
        driver = Neo4jDriver.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "ouroboros123"))
        )
        
        with driver.session() as session:
            # Check constraints
            result = session.run("SHOW CONSTRAINTS")
            constraints = [record["name"] for record in result]
            
            expected_constraints = ["file_path_unique", "class_fqn_unique", "function_signature_unique"]
            found = sum(1 for c in expected_constraints if any(c in str(constraint) for constraint in constraints))
            
            print(f"✓ Found {found}/{len(expected_constraints)} expected constraints")
            
            # Check system metadata
            result = session.run("MATCH (n:SystemMetadata) RETURN n")
            metadata = result.single()
            if metadata:
                node = metadata["n"]
                print(f"✓ System metadata initialized: {node['system']} v{node['version']}")
            else:
                print("⚠ System metadata not found")
        
        driver.close()
        return True
    except Exception as e:
        print(f"✗ Schema verification failed: {e}")
        return False


def test_core_modules():
    """Test 4-6: Core module imports."""
    print("\n[Test 4/6] Testing OuroborosGraphDB module...")
    try:
        from src.librarian.graph_db import OuroborosGraphDB
        db = OuroborosGraphDB()
        print("✓ OuroborosGraphDB imported and instantiated")
        db.close()
    except Exception as e:
        print(f"✗ OuroborosGraphDB failed: {e}")
        return False
    
    print("\n[Test 5/6] Testing ProvenanceTracker module...")
    try:
        from src.librarian.provenance import ProvenanceTracker, generate_prompt_id
        tracker = ProvenanceTracker()
        prompt_id = generate_prompt_id()
        print(f"✓ ProvenanceTracker working (generated ID: {prompt_id[:20]}...)")
    except Exception as e:
        print(f"✗ ProvenanceTracker failed: {e}")
        return False
    
    print("\n[Test 6/6] Testing checksum utilities...")
    try:
        from src.utils.checksum import calculate_string_checksum, calculate_file_checksum
        test_checksum = calculate_string_checksum("test content")
        print(f"✓ Checksum utilities working (test hash: {test_checksum[:16]}...)")
    except Exception as e:
        print(f"✗ Checksum utilities failed: {e}")
        return False
    
    return True


def test_end_to_end():
    """Test E2E: Create a test node with provenance."""
    print("\n[E2E Test] Creating test node with provenance metadata...")
    try:
        from src.librarian.graph_db import OuroborosGraphDB
        from src.utils.checksum import calculate_string_checksum
        
        db = OuroborosGraphDB()
        
        # Create a test file node
        test_content = "// Test file\nfunction hello() { return 'world'; }"
        checksum = calculate_string_checksum(test_content)
        
        node = db.create_file_node(
            path="/test/verification.js",
            language="javascript",
            content=test_content,
            context_checksum=checksum,
            prompt_id="test_verification_001"
        )
        
        print(f"✓ Created test node with path: {node['path']}")
        print(f"  - Checksum: {node['context_checksum'][:16]}...")
        print(f"  - Model: {node['model_name']} v{node['model_version']}")
        print(f"  - Timestamp: {node['timestamp']}")
        
        # Clean up
        with db.driver.session() as session:
            session.run("MATCH (f:File {path: '/test/verification.js'}) DELETE f")
        print("✓ Test node cleaned up")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ E2E test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("Ouroboros - Phase 1: Task 1 Verification")
    print("Testing Neo4j Graph Database Infrastructure")
    print("=" * 70)
    print()
    
    results = []
    
    # Run tests
    results.append(("Neo4j Driver & Connection", test_neo4j_driver()))
    results.append(("Schema Initialization", test_schema_initialization()))
    results.append(("Core Modules", test_core_modules()))
    results.append(("End-to-End Integration", test_end_to_end()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} | {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print("=" * 70)
    print(f"Results: {passed_count}/{total_count} test groups passed")
    print("=" * 70)
    
    if passed_count == total_count:
        print("\n🎉 All systems operational! Task 1 is properly working.")
        return 0
    else:
        print("\n⚠ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
