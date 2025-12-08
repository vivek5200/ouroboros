"""
Ouroboros - Code Ingestion Pipeline
Scans directories, parses code files, and ingests into Neo4j graph database.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.librarian.parser import CodeParser
from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.provenance import ProvenanceTracker, generate_prompt_id
from src.utils.checksum import calculate_file_checksum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.tree import Tree
from rich.panel import Panel
import typer

app = typer.Typer()
console = Console()


class IngestionPipeline:
    """
    Code ingestion pipeline with provenance tracking.
    """
    
    def __init__(self, database: OuroborosGraphDB, tracker: ProvenanceTracker):
        """
        Initialize ingestion pipeline.
        
        Args:
            database: Neo4j graph database connection
            tracker: Provenance metadata tracker
        """
        self.db = database
        self.tracker = tracker
        self.parser = CodeParser()
        self.stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'classes_created': 0,
            'functions_created': 0,
            'imports_created': 0,
            'errors': []
        }
    
    def scan_directory(self, root_path: str, exclude_patterns: Optional[List[str]] = None) -> List[str]:
        """
        Recursively scan directory for supported code files.
        
        Args:
            root_path: Root directory to scan
            exclude_patterns: List of patterns to exclude (e.g., 'node_modules', '__pycache__')
            
        Returns:
            List of file paths
        """
        exclude_patterns = exclude_patterns or ['node_modules', '__pycache__', 'venv', '.git', 'dist', 'build']
        files = []
        
        for root, dirs, filenames in os.walk(root_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if self.parser.detect_language(file_path):
                    files.append(file_path)
        
        return files
    
    def ingest_file(self, file_path: str, prompt_id: Optional[str] = None) -> bool:
        """
        Ingest a single file into the graph database.
        
        Args:
            file_path: Path to the file
            prompt_id: Unique operation identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate checksum
            checksum = calculate_file_checksum(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Detect language
            language = self.parser.detect_language(file_path)
            if not language:
                self.stats['files_skipped'] += 1
                return False
            
            # Generate prompt ID if not provided
            if not prompt_id:
                prompt_id = generate_prompt_id("ingest")
            
            # Create file node
            file_node = self.db.create_file_node(
                path=os.path.abspath(file_path),
                language=language,
                content=content,
                context_checksum=checksum,
                prompt_id=prompt_id
            )
            
            # Log provenance
            self.tracker.log_operation(
                operation_type="ingest_file",
                target=file_path,
                model_name=self.db.model_name,
                model_version=self.db.model_version,
                prompt_id=prompt_id,
                context_checksum=checksum
            )
            
            # Parse file structure
            parsed = self.parser.parse_file(file_path)
            if not parsed:
                self.stats['files_processed'] += 1
                return True
            
            # Ingest classes
            for class_def in parsed.get('classes', []):
                try:
                    self.db.create_class_node(
                        name=class_def.name,
                        fully_qualified_name=class_def.fully_qualified_name,
                        file_path=os.path.abspath(file_path),
                        start_line=class_def.start_line,
                        end_line=class_def.end_line,
                        is_exported=class_def.is_exported,
                        prompt_id=prompt_id
                    )
                    self.stats['classes_created'] += 1
                    
                    # Ingest class methods
                    for method in class_def.methods:
                        self.db.create_function_node(
                            name=method.name,
                            signature=method.signature,
                            file_path=os.path.abspath(file_path),
                            start_line=method.start_line,
                            end_line=method.end_line,
                            parent_class=class_def.fully_qualified_name,
                            is_async=method.is_async,
                            is_exported=False,
                            prompt_id=prompt_id
                        )
                        self.stats['functions_created'] += 1
                    
                    # Create inheritance edges
                    for parent_class in class_def.parent_classes:
                        # Note: This creates edge even if parent doesn't exist yet
                        # Will be resolved in graph construction phase
                        pass
                
                except Exception as e:
                    self.stats['errors'].append(f"Class {class_def.name} in {file_path}: {e}")
            
            # Ingest top-level functions
            for func_def in parsed.get('functions', []):
                try:
                    self.db.create_function_node(
                        name=func_def.name,
                        signature=func_def.signature,
                        file_path=os.path.abspath(file_path),
                        start_line=func_def.start_line,
                        end_line=func_def.end_line,
                        parent_class=None,
                        is_async=func_def.is_async,
                        is_exported=func_def.is_exported,
                        prompt_id=prompt_id
                    )
                    self.stats['functions_created'] += 1
                except Exception as e:
                    self.stats['errors'].append(f"Function {func_def.name} in {file_path}: {e}")
            
            # Store imports for graph construction phase
            for import_stmt in parsed.get('imports', []):
                self.stats['imports_created'] += 1
                # Import edges will be created in Task 3
            
            self.stats['files_processed'] += 1
            return True
        
        except Exception as e:
            self.stats['errors'].append(f"{file_path}: {e}")
            self.stats['files_skipped'] += 1
            return False
    
    def ingest_directory(self, root_path: str, exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Ingest all supported files in a directory.
        
        Args:
            root_path: Root directory to ingest
            exclude_patterns: Patterns to exclude
            
        Returns:
            Ingestion statistics
        """
        console.print(Panel.fit(
            f"[bold cyan]Ouroboros Ingestion Pipeline[/bold cyan]\n"
            f"Scanning: {root_path}",
            border_style="cyan"
        ))
        
        # Scan directory
        console.print("\n[yellow]Scanning directory...[/yellow]")
        files = self.scan_directory(root_path, exclude_patterns)
        console.print(f"[green]✓[/green] Found {len(files)} code files\n")
        
        if not files:
            console.print("[red]No supported files found![/red]")
            return self.stats
        
        # Ingest files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Ingesting files...", total=len(files))
            
            for file_path in files:
                progress.update(task, description=f"[cyan]Processing: {Path(file_path).name}")
                self.ingest_file(file_path)
                progress.advance(task)
        
        return self.stats


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to directory or file to ingest"),
    exclude: Optional[List[str]] = typer.Option(None, "--exclude", "-e", help="Patterns to exclude"),
    save_artifact: bool = typer.Option(True, "--save-artifact", help="Save provenance artifact")
):
    """
    Ingest source code into the Ouroboros graph database.
    
    Example:
        python scripts/ingest.py ./my-project --exclude node_modules --exclude dist
    """
    path_obj = Path(path)
    
    if not path_obj.exists():
        console.print(f"[red]Error: Path '{path}' does not exist![/red]")
        raise typer.Exit(1)
    
    # Initialize database and tracker
    db = OuroborosGraphDB()
    tracker = ProvenanceTracker(output_dir=str(Path.cwd()))
    pipeline = IngestionPipeline(db, tracker)
    
    try:
        # Ingest
        if path_obj.is_file():
            console.print(f"[cyan]Ingesting single file: {path}[/cyan]\n")
            pipeline.ingest_file(str(path_obj.absolute()))
        else:
            pipeline.ingest_directory(str(path_obj.absolute()), exclude)
        
        # Print statistics
        stats = pipeline.stats
        console.print("\n" + "=" * 70)
        console.print("[bold green]Ingestion Complete![/bold green]")
        console.print("=" * 70)
        console.print(f"Files processed:   {stats['files_processed']}")
        console.print(f"Files skipped:     {stats['files_skipped']}")
        console.print(f"Classes created:   {stats['classes_created']}")
        console.print(f"Functions created: {stats['functions_created']}")
        console.print(f"Imports detected:  {stats['imports_created']}")
        
        if stats['errors']:
            console.print(f"\n[yellow]Warnings/Errors: {len(stats['errors'])}[/yellow]")
            for error in stats['errors'][:5]:  # Show first 5 errors
                console.print(f"  • {error}")
            if len(stats['errors']) > 5:
                console.print(f"  ... and {len(stats['errors']) - 5} more")
        
        # Save provenance artifact
        if save_artifact:
            artifact_path = tracker.save_artifact("artifact_metadata.json")
            console.print(f"\n[green]✓[/green] Provenance artifact saved: {artifact_path}")
        
        console.print("=" * 70)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Ingestion interrupted by user[/yellow]")
        raise typer.Exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    app()
