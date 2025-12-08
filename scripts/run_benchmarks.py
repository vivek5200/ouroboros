"""Benchmark Test Runner - Execute and validate all 10 refactoring scenarios."""
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import ast
import hashlib

sys.path.insert(0, str(Path.cwd()))

from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.parser import CodeParser
from src.librarian.graph_constructor import GraphConstructor
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class BenchmarkResult:
    """Results for a single benchmark."""
    name: str
    compiles: bool
    graph_consistent: bool
    nodes_before: Dict[str, int]
    nodes_after: Dict[str, int]
    edges_before: Dict[str, int]
    edges_after: Dict[str, int]
    expected_changes: Dict[str, str]
    actual_changes: Dict[str, str]


class BenchmarkRunner:
    """Runs and validates synthetic benchmark refactors."""
    
    def __init__(self, db: OuroborosGraphDB):
        self.db = db
        self.parser = CodeParser()
        self.constructor = GraphConstructor(db)
        self.benchmark_dir = Path("tests/synthetic_benchmarks")
    
    def check_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check if Python file has valid syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            return True, "OK"
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
    
    def clear_graph(self):
        """Clear all nodes and relationships from graph."""
        with self.db.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def get_graph_stats(self) -> Dict[str, int]:
        """Get counts of nodes and relationships in graph."""
        with self.db.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (f:File) RETURN count(f) as count")
            file_count = result.single()["count"]
            
            result = session.run("MATCH (c:Class) RETURN count(c) as count")
            class_count = result.single()["count"]
            
            result = session.run("MATCH (f:Function) RETURN count(f) as count")
            function_count = result.single()["count"]
            
            # Count relationships
            result = session.run("MATCH ()-[r:IMPORTS]->() RETURN count(r) as count")
            imports_count = result.single()["count"]
            
            result = session.run("MATCH ()-[r:CONTAINS]->() RETURN count(r) as count")
            contains_count = result.single()["count"]
        
        return {
            "files": file_count,
            "classes": class_count,
            "functions": function_count,
            "imports": imports_count,
            "contains": contains_count,
        }
    
    def ingest_directory(self, directory: Path) -> int:
        """Ingest all Python files in directory."""
        from scripts.ingest import IngestionPipeline
        from src.librarian.provenance import ProvenanceTracker
        
        tracker = ProvenanceTracker(output_dir=".")
        pipeline = IngestionPipeline(self.db, tracker)
        files_ingested = 0
        
        for py_file in directory.glob("*.py"):
            try:
                metadata = pipeline.ingest_file(str(py_file))
                files_ingested += 1
            except Exception as e:
                console.print(f"[red]Error ingesting {py_file.name}: {e}[/red]")
        
        return files_ingested
    
    def run_benchmark(self, benchmark_name: str) -> BenchmarkResult:
        """Run a single benchmark refactor."""
        benchmark_path = self.benchmark_dir / benchmark_name
        before_dir = benchmark_path / "before"
        after_dir = benchmark_path / "after"
        
        # Check syntax for all files
        compiles = True
        for py_file in list(before_dir.glob("*.py")) + list(after_dir.glob("*.py")):
            valid, error = self.check_syntax(py_file)
            if not valid:
                console.print(f"[red]Syntax error in {py_file.name}: {error}[/red]")
                compiles = False
        
        # Clear graph and ingest BEFORE state
        self.clear_graph()
        self.ingest_directory(before_dir)
        self.constructor.construct_all_edges(str(before_dir))
        nodes_before = self.get_graph_stats()
        edges_before = nodes_before.copy()
        
        # Clear graph and ingest AFTER state
        self.clear_graph()
        self.ingest_directory(after_dir)
        self.constructor.construct_all_edges(str(after_dir))
        nodes_after = self.get_graph_stats()
        edges_after = nodes_after.copy()
        
        # Check graph consistency
        graph_consistent = self._validate_graph_consistency(
            benchmark_name, nodes_before, nodes_after
        )
        
        return BenchmarkResult(
            name=benchmark_name,
            compiles=compiles,
            graph_consistent=graph_consistent,
            nodes_before=nodes_before,
            nodes_after=nodes_after,
            edges_before=edges_before,
            edges_after=edges_after,
            expected_changes=self._get_expected_changes(benchmark_name),
            actual_changes=self._get_actual_changes(nodes_before, nodes_after),
        )
    
    def _validate_graph_consistency(
        self, benchmark_name: str, before: Dict, after: Dict
    ) -> bool:
        """Validate that graph changes match expected refactor."""
        expectations = {
            "01_rename_import": lambda b, a: a["files"] == b["files"],
            "02_move_function": lambda b, a: a["files"] == b["files"] and a["functions"] == b["functions"],
            "03_change_signature": lambda b, a: a["functions"] == b["functions"],
            "04_extract_class": lambda b, a: a["classes"] == b["classes"] + 1,
            "05_inline_function": lambda b, a: a["functions"] == b["functions"] - 1,
            "06_rename_variable": lambda b, a: a["classes"] == b["classes"],
            "07_change_parameter": lambda b, a: a["classes"] == b["classes"],
            "08_add_method": lambda b, a: a["functions"] > b["functions"],
            "09_remove_method": lambda b, a: a["functions"] < b["functions"],
            "10_refactor_conditional": lambda b, a: a["functions"] == b["functions"],
        }
        
        if benchmark_name in expectations:
            return expectations[benchmark_name](before, after)
        return True
    
    def _get_expected_changes(self, benchmark_name: str) -> Dict[str, str]:
        """Get expected changes for benchmark."""
        expectations = {
            "01_rename_import": {"files": "renamed", "imports": "updated"},
            "02_move_function": {"functions": "moved", "contains": "updated"},
            "03_change_signature": {"functions": "signature changed"},
            "04_extract_class": {"classes": "+1", "functions": "restructured"},
            "05_inline_function": {"functions": "-1"},
            "06_rename_variable": {"variables": "renamed"},
            "07_change_parameter": {"parameters": "renamed"},
            "08_add_method": {"functions": "+3"},
            "09_remove_method": {"functions": "-1"},
            "10_refactor_conditional": {"logic": "simplified"},
        }
        return expectations.get(benchmark_name, {})
    
    def _get_actual_changes(self, before: Dict, after: Dict) -> Dict[str, str]:
        """Calculate actual changes between states."""
        changes = {}
        for key in before.keys():
            diff = after[key] - before[key]
            if diff != 0:
                changes[key] = f"{'+' if diff > 0 else ''}{diff}"
        return changes
    
    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all 10 benchmark refactors."""
        benchmarks = [
            "01_rename_import",
            "02_move_function",
            "03_change_signature",
            "04_extract_class",
            "05_inline_function",
            "06_rename_variable",
            "07_change_parameter",
            "08_add_method",
            "09_remove_method",
            "10_refactor_conditional",
        ]
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running benchmarks...", total=len(benchmarks))
            
            for benchmark in benchmarks:
                progress.update(task, description=f"[cyan]Running {benchmark}...")
                result = self.run_benchmark(benchmark)
                results.append(result)
                progress.advance(task)
        
        return results


def main():
    """Run all benchmarks and display results."""
    console.print("\n[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  TASK 4: Synthetic Test Suite Runner[/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]\n")
    
    db = OuroborosGraphDB()
    runner = BenchmarkRunner(db)
    
    console.print("[yellow]Executing 10 benchmark refactors...[/yellow]\n")
    results = runner.run_all_benchmarks()
    
    # Display results table
    table = Table(title="Benchmark Results")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Benchmark", style="cyan", width=25)
    table.add_column("Compiles", justify="center", width=10)
    table.add_column("Graph OK", justify="center", width=10)
    table.add_column("Changes", style="yellow", width=30)
    
    passed = 0
    for i, result in enumerate(results, 1):
        compiles_icon = "✅" if result.compiles else "❌"
        graph_icon = "✅" if result.graph_consistent else "❌"
        changes = ", ".join([f"{k}{v}" for k, v in result.actual_changes.items()])
        
        table.add_row(
            str(i),
            result.name,
            compiles_icon,
            graph_icon,
            changes if changes else "no changes",
        )
        
        if result.compiles and result.graph_consistent:
            passed += 1
    
    console.print(table)
    
    # Summary
    console.print(f"\n[bold]Results: {passed}/{len(results)} benchmarks passed[/bold]")
    
    if passed == len(results):
        console.print("\n🎉 [bold green]ALL BENCHMARKS PASSED![/bold green]")
    else:
        console.print(f"\n⚠ [yellow]{len(results) - passed} benchmarks failed[/yellow]")
    
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]\n")
    
    db.close()


if __name__ == "__main__":
    main()
