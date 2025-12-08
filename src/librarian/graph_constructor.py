"""
Ouroboros - Graph Construction Module
Creates relationships (edges) between nodes in the graph database.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.librarian.parser import CodeParser
from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.provenance import generate_prompt_id
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


class GraphConstructor:
    """
    Constructs relationships between nodes in the graph database.
    Handles IMPORTS, INHERITS_FROM, and CALLS edges.
    """
    
    def __init__(self, database: OuroborosGraphDB):
        self.db = database
        self.parser = CodeParser()
        self.stats = {
            'imports_created': 0,
            'inheritance_created': 0,
            'calls_created': 0,
            'errors': []
        }
    
    def resolve_import_path(self, source_file: str, import_path: str, base_dir: str) -> Optional[str]:
        """
        Resolve relative import path to absolute file path.
        
        Args:
            source_file: Absolute path of the file containing the import
            import_path: The import path (e.g., './types', '../utils')
            base_dir: Base directory of the project
            
        Returns:
            Absolute path to the imported file, or None if not found
        """
        source_path = Path(source_file)
        source_dir = source_path.parent
        
        # Handle relative imports
        if import_path.startswith('.'):
            resolved = (source_dir / import_path).resolve()
        else:
            # Absolute import from base
            resolved = (Path(base_dir) / import_path).resolve()
        
        # Try common extensions
        extensions = ['', '.js', '.ts', '.jsx', '.tsx', '.py']
        for ext in extensions:
            candidate = Path(str(resolved) + ext)
            if candidate.exists() and candidate.is_file():
                return str(candidate.absolute())
        
        # Try index files for directory imports
        for ext in ['.js', '.ts', '.jsx', '.tsx']:
            candidate = resolved / f'index{ext}'
            if candidate.exists():
                return str(candidate.absolute())
        
        # Try __init__.py for Python packages
        init_file = resolved / '__init__.py'
        if init_file.exists():
            return str(init_file.absolute())
        
        return None
    
    def construct_import_edges(self, base_dir: str) -> int:
        """
        Create IMPORTS edges between files based on import statements.
        
        Args:
            base_dir: Base directory of the project
            
        Returns:
            Number of edges created
        """
        console.print("[cyan]Constructing import relationships...[/cyan]")
        
        with self.db.driver.session() as session:
            # Get all files
            result = session.run("MATCH (f:File) RETURN f.path AS path")
            files = [record["path"] for record in result]
        
        edges_created = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing imports...", total=len(files))
            
            for file_path in files:
                try:
                    parsed = self.parser.parse_file(file_path)
                    if not parsed:
                        progress.advance(task)
                        continue
                    
                    for import_stmt in parsed.get('imports', []):
                        target_path = self.resolve_import_path(
                            file_path,
                            import_stmt.source_file,
                            base_dir
                        )
                        
                        if target_path:
                            # Check if target exists in database
                            with self.db.driver.session() as session:
                                check = session.run(
                                    "MATCH (f:File {path: $path}) RETURN count(f) AS count",
                                    path=target_path
                                )
                                if check.single()["count"] > 0:
                                    self.db.create_import_edge(
                                        from_file=file_path,
                                        to_file=target_path,
                                        import_names=import_stmt.imported_symbols,
                                        prompt_id=generate_prompt_id("graph_construct")
                                    )
                                    edges_created += 1
                                    self.stats['imports_created'] += 1
                
                except Exception as e:
                    self.stats['errors'].append(f"Import edge for {Path(file_path).name}: {e}")
                
                progress.advance(task)
        
        console.print(f"[green]✓[/green] Created {edges_created} IMPORTS edges")
        return edges_created
    
    def construct_inheritance_edges(self) -> int:
        """
        Create INHERITS_FROM edges between classes.
        
        Returns:
            Number of edges created
        """
        console.print("[cyan]Constructing inheritance relationships...[/cyan]")
        
        with self.db.driver.session() as session:
            # Get all files with their classes
            result = session.run("""
                MATCH (f:File)
                RETURN f.path AS path
            """)
            files = [record["path"] for record in result]
        
        edges_created = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing inheritance...", total=len(files))
            
            for file_path in files:
                try:
                    parsed = self.parser.parse_file(file_path)
                    if not parsed:
                        progress.advance(task)
                        continue
                    
                    for class_def in parsed.get('classes', []):
                        for parent_class in class_def.parent_classes:
                            # Try to find parent class in database
                            with self.db.driver.session() as session:
                                # First try exact FQN match
                                result = session.run("""
                                    MATCH (c:Class {fully_qualified_name: $parent})
                                    RETURN c.fully_qualified_name AS fqn
                                """, parent=parent_class)
                                
                                parent_fqn = None
                                record = result.single()
                                if record:
                                    parent_fqn = record["fqn"]
                                else:
                                    # Try matching by class name only
                                    result = session.run("""
                                        MATCH (c:Class {name: $parent})
                                        RETURN c.fully_qualified_name AS fqn
                                    """, parent=parent_class)
                                    record = result.single()
                                    if record:
                                        parent_fqn = record["fqn"]
                                
                                if parent_fqn:
                                    self.db.create_inherits_edge(
                                        child_class=class_def.fully_qualified_name,
                                        parent_class=parent_fqn,
                                        prompt_id=generate_prompt_id("graph_construct")
                                    )
                                    edges_created += 1
                                    self.stats['inheritance_created'] += 1
                
                except Exception as e:
                    self.stats['errors'].append(f"Inheritance edge for {Path(file_path).name}: {e}")
                
                progress.advance(task)
        
        console.print(f"[green]✓[/green] Created {edges_created} INHERITS_FROM edges")
        return edges_created
    
    def construct_call_edges(self) -> int:
        """
        Create CALLS edges between functions based on call graph analysis.
        
        Returns:
            Number of edges created
        """
        console.print("[cyan]Constructing function call relationships...[/cyan]")
        
        # Get all files from database
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (f:File)
                RETURN f.path AS path
            """)
            files = [record["path"] for record in result]
        
        edges_created = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing function calls...", total=len(files))
            
            for file_path in files:
                try:
                    if not Path(file_path).exists():
                        progress.advance(task)
                        continue
                    
                    parsed = self.parser.parse_file(file_path)
                    if not parsed:
                        progress.advance(task)
                        continue
                    
                    # Process function calls in top-level functions
                    for func_def in parsed.get('functions', []):
                        for call_name in func_def.calls:
                            if self._create_call_edge(func_def.name, call_name, file_path):
                                edges_created += 1
                    
                    # Process function calls in class methods
                    for class_def in parsed.get('classes', []):
                        for method in class_def.methods:
                            for call_name in method.calls:
                                if self._create_call_edge(method.name, call_name, file_path):
                                    edges_created += 1
                    
                except Exception as e:
                    self.stats['errors'].append(f"Call edges for {Path(file_path).name}: {e}")
                
                progress.advance(task)
        
        console.print(f"[green]✓[/green] Created {edges_created} CALLS edges")
        self.stats['calls_created'] = edges_created
        return edges_created
    
    def _create_call_edge(self, caller_name: str, callee_name: str, file_path: str) -> bool:
        """
        Create a CALLS edge between two functions using fuzzy matching.
        
        Args:
            caller_name: Name of the calling function
            callee_name: Name of the called function
            file_path: Path of file containing the caller
        
        Returns:
            True if edge was created, False otherwise
        """
        try:
            with self.db.driver.session() as session:
                # Find caller function
                result = session.run("""
                    MATCH (f:File {path: $path})-[:CONTAINS*1..2]->(caller:Function {name: $caller_name})
                    RETURN caller
                    LIMIT 1
                """, path=file_path, caller_name=caller_name)
                
                if not result.single():
                    return False
                
                # Find callee function (fuzzy match by name only)
                # Try in same file first, then anywhere in codebase
                result = session.run("""
                    MATCH (callee:Function {name: $callee_name})
                    RETURN callee
                    ORDER BY 
                        CASE WHEN exists((f:File {path: $path})-[:CONTAINS*1..2]->(callee)) 
                        THEN 0 ELSE 1 END
                    LIMIT 1
                """, callee_name=callee_name, path=file_path)
                
                if not result.single():
                    return False
                
                # Create CALLS edge
                self.db.create_calls_edge(
                    caller_name=caller_name,
                    callee_name=callee_name,
                    file_path=file_path,
                    prompt_id=generate_prompt_id("call_graph")
                )
                
                return True
        except Exception:
            return False
    
    def construct_all_edges(self, base_dir: str) -> Dict[str, int]:
        """
        Construct all relationship edges in the graph.
        
        Args:
            base_dir: Base directory of the project
            
        Returns:
            Statistics dictionary
        """
        console.print("\n[bold cyan]Graph Construction Pipeline[/bold cyan]\n")
        
        # Phase 1: Import edges
        self.construct_import_edges(base_dir)
        
        # Phase 2: Inheritance edges
        self.construct_inheritance_edges()
        
        # Phase 3: Call edges (placeholder)
        self.construct_call_edges()
        
        return self.stats
