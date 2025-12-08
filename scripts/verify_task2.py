"""
Verify Task 2: Ingestion Pipeline
Query the database to confirm data was ingested correctly.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.librarian.graph_db import OuroborosGraphDB
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def verify_ingestion():
    """Verify the ingestion pipeline results."""
    console.print(Panel.fit(
        "[bold cyan]Task 2: Ingestion Pipeline Verification[/bold cyan]",
        border_style="cyan"
    ))
    
    db = OuroborosGraphDB()
    
    try:
        with db.driver.session() as session:
            # Test 1: Count files
            console.print("\n[yellow]Test 1: Counting ingested files...[/yellow]")
            result = session.run("MATCH (f:File) RETURN count(f) AS count")
            file_count = result.single()["count"]
            console.print(f"  ✓ Files in database: {file_count}")
            
            # Test 2: List files with metadata
            console.print("\n[yellow]Test 2: Listing files with provenance...[/yellow]")
            result = session.run("""
                MATCH (f:File) 
                RETURN f.path AS path, f.language AS language, 
                       f.model_version AS version, f.line_count AS lines
                ORDER BY f.path
            """)
            
            table = Table(title="Ingested Files")
            table.add_column("Path", style="cyan")
            table.add_column("Language", style="green")
            table.add_column("Lines", style="yellow")
            table.add_column("Model Ver", style="magenta")
            
            for record in result:
                path = Path(record["path"]).name
                table.add_row(
                    path,
                    record["language"],
                    str(record["lines"]),
                    record["version"]
                )
            
            console.print(table)
            
            # Test 3: Count classes
            console.print("\n[yellow]Test 3: Counting classes...[/yellow]")
            result = session.run("MATCH (c:Class) RETURN count(c) AS count")
            class_count = result.single()["count"]
            console.print(f"  ✓ Classes in database: {class_count}")
            
            # Test 4: List classes
            console.print("\n[yellow]Test 4: Listing classes...[/yellow]")
            result = session.run("""
                MATCH (f:File)-[:CONTAINS]->(c:Class)
                RETURN c.name AS name, c.fully_qualified_name AS fqn, 
                       f.path AS file, c.is_exported AS exported
                ORDER BY c.name
            """)
            
            table = Table(title="Extracted Classes")
            table.add_column("Class Name", style="cyan")
            table.add_column("FQN", style="green")
            table.add_column("Exported", style="yellow")
            table.add_column("File", style="magenta")
            
            for record in result:
                table.add_row(
                    record["name"],
                    record["fqn"],
                    "✓" if record["exported"] else "✗",
                    Path(record["file"]).name
                )
            
            console.print(table)
            
            # Test 5: Count functions
            console.print("\n[yellow]Test 5: Counting functions...[/yellow]")
            result = session.run("MATCH (fn:Function) RETURN count(fn) AS count")
            function_count = result.single()["count"]
            console.print(f"  ✓ Functions in database: {function_count}")
            
            # Test 6: Sample functions
            console.print("\n[yellow]Test 6: Sample functions (first 10)...[/yellow]")
            result = session.run("""
                MATCH (fn:Function)
                OPTIONAL MATCH (c:Class)-[:CONTAINS]->(fn)
                RETURN fn.name AS name, fn.is_async AS is_async, 
                       c.name AS parent_class
                ORDER BY fn.name
                LIMIT 10
            """)
            
            table = Table(title="Sample Functions")
            table.add_column("Function", style="cyan")
            table.add_column("Async", style="green")
            table.add_column("Parent Class", style="yellow")
            
            for record in result:
                table.add_row(
                    record["name"],
                    "✓" if record["is_async"] else "✗",
                    record["parent_class"] or "(top-level)"
                )
            
            console.print(table)
            
            # Test 7: Check provenance metadata
            console.print("\n[yellow]Test 7: Verifying provenance metadata...[/yellow]")
            result = session.run("""
                MATCH (f:File)
                WHERE f.context_checksum IS NOT NULL
                RETURN count(f) AS count
            """)
            checksum_count = result.single()["count"]
            console.print(f"  ✓ Files with checksums: {checksum_count}/{file_count}")
            
            result = session.run("""
                MATCH (f:File)
                WHERE f.timestamp IS NOT NULL
                RETURN count(f) AS count
            """)
            timestamp_count = result.single()["count"]
            console.print(f"  ✓ Files with timestamps: {timestamp_count}/{file_count}")
            
            # Summary
            console.print("\n" + "=" * 70)
            console.print("[bold green]Verification Summary[/bold green]")
            console.print("=" * 70)
            console.print(f"Files:     {file_count}")
            console.print(f"Classes:   {class_count}")
            console.print(f"Functions: {function_count}")
            console.print("=" * 70)
            
            all_pass = (
                file_count > 0 and
                class_count > 0 and
                function_count > 0 and
                checksum_count == file_count and
                timestamp_count == file_count
            )
            
            if all_pass:
                console.print("\n[bold green]🎉 All tests passed! Ingestion pipeline is working correctly.[/bold green]")
            else:
                console.print("\n[bold red]⚠ Some tests failed. Please review the output above.[/bold red]")
    
    finally:
        db.close()


if __name__ == "__main__":
    verify_ingestion()
