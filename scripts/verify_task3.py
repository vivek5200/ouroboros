"""Verify Task 3: Graph Construction Logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.librarian.graph_db import OuroborosGraphDB
from rich.console import Console
from rich.table import Table

console = Console()

def test_graph_edges():
    """Test 1: Verify relationship edges exist."""
    console.print("\n[bold cyan]TEST 1: Graph Edges Verification[/bold cyan]")
    
    db = OuroborosGraphDB()
    
    # Count relationship types
    with db.driver.session() as session:
        result = session.run("""
            MATCH ()-[r:IMPORTS]->()
            RETURN count(r) as count
        """)
        imports_count = result.single()["count"]
        
        result = session.run("""
            MATCH ()-[r:INHERITS_FROM]->()
            RETURN count(r) as count
        """)
        inherits_count = result.single()["count"]
        
        result = session.run("""
            MATCH ()-[r:CALLS]->()
            RETURN count(r) as count
        """)
        calls_count = result.single()["count"]
    
    table = Table(title="Relationship Counts")
    table.add_column("Edge Type", style="cyan")
    table.add_column("Count", style="green")
    
    table.add_row("IMPORTS", str(imports_count))
    table.add_row("INHERITS_FROM", str(inherits_count))
    table.add_row("CALLS", str(calls_count))
    
    console.print(table)
    
    db.close()
    
    # Pass criteria: at least 1 relationship exists
    passed = imports_count > 0
    
    if passed:
        console.print("\n✅ [green]PASS[/green]: Graph edges exist")
    else:
        console.print("\n❌ [red]FAIL[/red]: No graph edges found")
    
    return passed


def test_import_edges():
    """Test 2: Inspect specific IMPORTS edges."""
    console.print("\n[bold cyan]TEST 2: IMPORTS Edge Inspection[/bold cyan]")
    
    db = OuroborosGraphDB()
    
    with db.driver.session() as session:
        result = session.run("""
            MATCH (source:File)-[r:IMPORTS]->(target:File)
            RETURN source.path as source_path, 
                   target.path as target_path,
                   r.model_name as model_name,
                   r.timestamp as timestamp
            LIMIT 10
        """)
        
        records = list(result)
    
    if records:
        table = Table(title="IMPORTS Relationships")
        table.add_column("Source File", style="cyan")
        table.add_column("→ Target File", style="green")
        table.add_column("Model", style="yellow")
        
        for record in records:
            source = Path(record["source_path"]).name
            target = Path(record["target_path"]).name
            model = record["model_name"]
            table.add_row(source, target, model)
        
        console.print(table)
        console.print(f"\n✅ [green]PASS[/green]: Found {len(records)} IMPORTS edges")
        passed = True
    else:
        console.print("\n⚠ [yellow]INFO[/yellow]: No IMPORTS edges found")
        passed = False
    
    db.close()
    return passed


def test_subgraph_retrieval():
    """Test 3: Retrieve subgraph for a specific file."""
    console.print("\n[bold cyan]TEST 3: Subgraph Retrieval[/bold cyan]")
    
    db = OuroborosGraphDB()
    
    # Get a file node
    with db.driver.session() as session:
        result = session.run("""
            MATCH (f:File)
            RETURN f.path as path
            LIMIT 1
        """)
        record = result.single()
        if not record:
            console.print("\n⚠ [yellow]SKIP[/yellow]: No files in database")
            db.close()
            return False
        
        file_path = record["path"]
        
        # Get subgraph: file + its classes + functions + imports
        result = session.run("""
            MATCH (f:File {path: $path})
            OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
            OPTIONAL MATCH (c)-[:CONTAINS]->(m:Function)
            OPTIONAL MATCH (f)-[:CONTAINS]->(func:Function)
            OPTIONAL MATCH (f)-[:IMPORTS]->(imported:File)
            RETURN f, 
                   collect(DISTINCT c) as classes,
                   collect(DISTINCT m) as methods,
                   collect(DISTINCT func) as functions,
                   collect(DISTINCT imported) as imports
        """, path=file_path)
        
        record = result.single()
    
    console.print(f"\n[bold]File:[/bold] {Path(file_path).name}")
    console.print(f"  Classes:   {len(record['classes'])}")
    console.print(f"  Methods:   {len(record['methods'])}")
    console.print(f"  Functions: {len(record['functions'])}")
    console.print(f"  Imports:   {len(record['imports'])}")
    
    for imp in record['imports']:
        console.print(f"    → {Path(imp['path']).name}")
    
    console.print("\n✅ [green]PASS[/green]: Subgraph retrieval successful")
    
    db.close()
    return True


def test_traversal_query():
    """Test 4: Multi-hop graph traversal."""
    console.print("\n[bold cyan]TEST 4: Graph Traversal (2-hop)[/bold cyan]")
    
    db = OuroborosGraphDB()
    
    with db.driver.session() as session:
        # Find all files within 2 hops of any file
        result = session.run("""
            MATCH path = (start:File)-[*1..2]-(connected)
            WHERE start.path CONTAINS 'app.js'
            RETURN 
                start.path as start_file,
                [node in nodes(path) | labels(node)[0] + ': ' + coalesce(node.name, node.path)] as path_nodes,
                length(path) as hops
            LIMIT 5
        """)
        
        records = list(result)
    
    if records:
        for i, record in enumerate(records, 1):
            console.print(f"\n[bold]Path {i}:[/bold]")
            console.print(f"  Start: {Path(record['start_file']).name}")
            console.print(f"  Hops: {record['hops']}")
            console.print(f"  Path: {' → '.join([str(n).split(': ')[1] for n in record['path_nodes']])}")
        
        console.print(f"\n✅ [green]PASS[/green]: Found {len(records)} traversal paths")
        passed = True
    else:
        console.print("\n⚠ [yellow]INFO[/yellow]: No multi-hop paths found (may need more edges)")
        passed = False
    
    db.close()
    return passed


def main():
    """Run all verification tests."""
    console.print("\n[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  TASK 3 VERIFICATION: Graph Construction[/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    
    tests = [
        test_graph_edges,
        test_import_edges,
        test_subgraph_retrieval,
        test_traversal_query,
    ]
    
    results = []
    for test in tests:
        try:
            passed = test()
            results.append(passed)
        except Exception as e:
            console.print(f"\n❌ [red]ERROR[/red]: {e}")
            results.append(False)
    
    # Summary
    console.print("\n[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    console.print(f"[bold]Tests Passed: {sum(results)}/{len(results)}[/bold]")
    
    if all(results):
        console.print("\n🎉 [bold green]ALL TESTS PASSED[/bold green] - Task 3 Complete!")
    else:
        console.print("\n⚠ [yellow]PARTIAL SUCCESS[/yellow] - Some tests failed")
    
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]\n")


if __name__ == "__main__":
    main()
