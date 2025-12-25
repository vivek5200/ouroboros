#!/usr/bin/env python3
"""
Ouroboros CLI - Command-line interface for AI-powered code refactoring

This CLI provides a user-friendly interface to the Ouroboros code generation pipeline.
It supports:
- Refactoring code with AI assistance
- Safety gates and syntax validation
- Provenance logging for auditability
- Interactive and non-interactive modes

Usage:
    ouroboros refactor "Add caching to user service" --target src/user_service.py
    ouroboros refactor "Migrate to PyTorch" --target src/models.py --safe-mode
    ouroboros apply --run-id gen_20250121_123456 --max-risk 0.3
    ouroboros status --run-id gen_20250121_123456

Created: 2025-12-21 (Phase 5 implementation)
"""

import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich import print as rprint
import json
import logging
from datetime import datetime

# Import Ouroboros components
from src.ouroboros_pipeline import OuroborosCodeGenerator, GenerationRequest, GenerationResult
from src.diffusion.config import FAST_CONFIG, BALANCED_CONFIG, QUALITY_CONFIG
from src.utils.provenance_logger import ProvenanceLogger

# Initialize CLI app
app = typer.Typer(
    name="ouroboros",
    help="🐍 Ouroboros - AI-Powered Code Refactoring with Discrete Diffusion",
    add_completion=False,
)

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@app.command()
def refactor(
    description: str = typer.Argument(
        ...,
        help="Description of the refactoring task (e.g., 'Add caching to user lookup')"
    ),
    target: List[str] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target files to refactor (can specify multiple)"
    ),
    functions: List[str] = typer.Option(
        None,
        "--function",
        "-f",
        help="Specific functions to refactor (can specify multiple)"
    ),
    config: str = typer.Option(
        "balanced",
        "--config",
        "-c",
        help="Generation config: fast, balanced, or quality"
    ),
    safe_mode: bool = typer.Option(
        True,
        "--safe-mode/--no-safe-mode",
        help="Enable safety gate (syntax validation + retry)"
    ),
    max_risk: float = typer.Option(
        0.5,
        "--max-risk",
        help="Maximum risk score for auto-apply (0.0-1.0)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without making changes"
    ),
    auto_apply: bool = typer.Option(
        False,
        "--auto-apply",
        help="Automatically apply patches below max-risk threshold"
    ),
    neo4j_uri: str = typer.Option(
        "bolt://localhost:7687",
        "--neo4j-uri",
        help="Neo4j database URI"
    ),
    neo4j_user: str = typer.Option(
        "neo4j",
        "--neo4j-user",
        help="Neo4j username"
    ),
    neo4j_password: str = typer.Option(
        "password",
        "--neo4j-password",
        help="Neo4j password"
    ),
    ai21_api_key: Optional[str] = typer.Option(
        None,
        "--ai21-key",
        help="AI21 API key for Jamba compression"
    ),
    mock_mode: bool = typer.Option(
        False,
        "--mock",
        help="Use mock mode for testing (no real API calls)"
    ),
):
    """
    🔧 Refactor code using Ouroboros AI pipeline.
    
    Examples:
    
        # Refactor specific file
        ouroboros refactor "Add caching" --target src/user_service.py
        
        # Multiple targets with quality mode
        ouroboros refactor "Optimize queries" -t src/db.py -t src/cache.py -c quality
        
        # Auto-apply safe changes
        ouroboros refactor "Add type hints" -t src/utils.py --auto-apply --max-risk 0.3
        
        # Safe mode with dry run
        ouroboros refactor "Migrate to async" -t src/api.py --safe-mode --dry-run
    """
    console.print(Panel.fit(
        "[bold blue]🐍 Ouroboros Code Refactoring[/bold blue]\n"
        f"Task: {description}",
        border_style="blue"
    ))
    
    # Transparency warnings
    warnings = []
    if mock_mode:
        warnings.append("[yellow]⚠️  MOCK MODE: Using simulated responses (no real API calls)[/yellow]")
    if not safe_mode:
        warnings.append("[red]⚠️  SAFETY GATE DISABLED: Syntax validation and semantic analysis are OFF[/red]")
    
    if warnings:
        console.print(Panel(
            "\n".join(warnings),
            title="[bold yellow]⚠️  Warnings[/bold yellow]",
            border_style="yellow"
        ))
    
    # Validate inputs
    if not target and not functions:
        console.print("[red]Error: Must specify at least one --target file or --function[/red]")
        raise typer.Exit(1)
    
    if config not in ["fast", "balanced", "quality"]:
        console.print(f"[red]Error: Invalid config '{config}'. Use: fast, balanced, or quality[/red]")
        raise typer.Exit(1)
    
    # Convert target files to Paths
    target_paths = [Path(f) for f in target] if target else []
    
    # Check if files exist (unless mock mode)
    if not mock_mode:
        for path in target_paths:
            if not path.exists():
                console.print(f"[red]Error: File not found: {path}[/red]")
                raise typer.Exit(1)
    
    # Initialize generator
    console.print("\n[cyan]Initializing Ouroboros pipeline...[/cyan]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            init_task = progress.add_task("Connecting to services...", total=None)
            
            generator = OuroborosCodeGenerator(
                neo4j_uri=neo4j_uri,
                neo4j_user=neo4j_user,
                neo4j_password=neo4j_password,
                ai21_api_key=ai21_api_key,
                use_mock=mock_mode,
                skip_db_init=mock_mode
            )
            
            progress.update(init_task, completed=True)
            
            # Show model configuration transparency
            if config == "mock" or mock_mode:
                console.print("\n[yellow]📝 Using MOCK diffusion model (no real generation)[/yellow]")
            else:
                config_map = {
                    "fast": "Qwen2.5-Coder-1.5B (20 steps)",
                    "balanced": "Qwen2.5-Coder-7B (50 steps)",
                    "quality": "Qwen2.5-Coder-14B (100 steps)"
                }
                console.print(f"\n[cyan]🤖 Model: {config_map.get(config, config)}[/cyan]")
            
            if safe_mode:
                console.print("[green]🛡️  Safety Gate: ENABLED (syntax + semantic validation)[/green]")
            else:
                console.print("[red]⚠️  Safety Gate: DISABLED[/red]")
    
    except Exception as e:
        console.print(f"[red]Failed to initialize: {e}[/red]")
        raise typer.Exit(1)
    
    # Generate patches
    console.print(f"\n[cyan]Generating refactor patches with {config} config...[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        gen_task = progress.add_task("Analyzing and generating code...", total=None)
        
        result: GenerationResult = generator.generate(
            issue_description=description,
            target_files=[str(p) for p in target_paths] if target_paths else None,
            target_functions=functions,
            config=config
        )
        
        progress.update(gen_task, completed=True)
    
    # Display results
    _display_results(result, console)
    
    # Apply patches if requested
    if auto_apply and not dry_run:
        applicable_patches = result.get_applicable_patches(max_risk=max_risk)
        
        if applicable_patches:
            console.print(f"\n[cyan]Auto-applying {len(applicable_patches)} patches...[/cyan]")
            
            for patch in applicable_patches:
                success = generator.apply_patch(patch, backup=True, dry_run=False)
                if success:
                    console.print(f"  [green]✓[/green] Applied: {patch.file_path}")
                else:
                    console.print(f"  [red]✗[/red] Failed: {patch.file_path}")
        else:
            console.print("\n[yellow]No applicable patches to auto-apply[/yellow]")
    
    elif dry_run:
        console.print("\n[yellow]Dry run mode - no changes made[/yellow]")
    
    else:
        # Show instructions for manual application
        applicable_patches = result.get_applicable_patches(max_risk=max_risk)
        if applicable_patches:
            console.print(
                f"\n[cyan]💡 Tip: Use --auto-apply to automatically apply "
                f"{len(applicable_patches)} safe patches[/cyan]"
            )
    
    # Show provenance file
    if "provenance_file" in result.metadata:
        console.print(f"\n[dim]Provenance metadata: {result.metadata['provenance_file']}[/dim]")
    
    generator.close()


@app.command()
def status(
    run_id: str = typer.Option(
        None,
        "--run-id",
        "-r",
        help="Run ID to check status"
    ),
    latest: bool = typer.Option(
        False,
        "--latest",
        "-l",
        help="Show status of latest run"
    ),
):
    """
    📊 Check status of a generation run.
    
    Examples:
        ouroboros status --run-id gen_20250121_123456
        ouroboros status --latest
    """
    if not run_id and not latest:
        console.print("[red]Error: Must specify --run-id or --latest[/red]")
        raise typer.Exit(1)
    
    artifacts_dir = Path("./artifacts")
    
    if not artifacts_dir.exists():
        console.print("[yellow]No artifacts found[/yellow]")
        raise typer.Exit(0)
    
    # Find provenance file
    if latest:
        # Find most recent provenance file
        provenance_files = sorted(
            artifacts_dir.glob("artifact_metadata_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not provenance_files:
            console.print("[yellow]No provenance files found[/yellow]")
            raise typer.Exit(0)
        
        provenance_file = provenance_files[0]
    else:
        # Find by run_id
        provenance_file = artifacts_dir / f"artifact_metadata_{run_id}.json"
        
        if not provenance_file.exists():
            # Try with _failed suffix
            provenance_file = artifacts_dir / f"artifact_metadata_{run_id}_failed.json"
            
            if not provenance_file.exists():
                console.print(f"[red]Provenance file not found for run: {run_id}[/red]")
                raise typer.Exit(1)
    
    # Load and display provenance
    try:
        with open(provenance_file) as f:
            provenance = json.load(f)
        
        _display_provenance(provenance, console)
    
    except Exception as e:
        console.print(f"[red]Failed to load provenance: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_runs(
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of runs to show"
    ),
):
    """
    📝 List recent generation runs.
    
    Example:
        ouroboros list-runs --limit 20
    """
    artifacts_dir = Path("./artifacts")
    
    if not artifacts_dir.exists():
        console.print("[yellow]No artifacts found[/yellow]")
        raise typer.Exit(0)
    
    # Find all provenance files
    provenance_files = sorted(
        artifacts_dir.glob("artifact_metadata_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:limit]
    
    if not provenance_files:
        console.print("[yellow]No provenance files found[/yellow]")
        raise typer.Exit(0)
    
    # Create table
    table = Table(title=f"Recent Generation Runs (Latest {len(provenance_files)})")
    table.add_column("Run ID", style="cyan")
    table.add_column("Task", style="white")
    table.add_column("Duration", justify="right", style="yellow")
    table.add_column("Status", justify="center")
    table.add_column("Files", justify="right", style="blue")
    table.add_column("Timestamp", style="dim")
    
    for prov_file in provenance_files:
        try:
            with open(prov_file) as f:
                prov = json.load(f)
            
            run_id = prov.get("run_id", "unknown")
            task = prov.get("issue_description", "")[:40]
            duration = f"{prov.get('duration_seconds', 0):.1f}s"
            success = prov.get("success", False)
            status = "[green]✓[/green]" if success else "[red]✗[/red]"
            num_files = len(prov.get("file_modifications", []))
            timestamp = prov.get("timestamp_start", "")[:19]
            
            table.add_row(run_id, task, duration, status, str(num_files), timestamp)
        
        except Exception:
            continue
    
    console.print(table)


def _display_results(result: GenerationResult, console: Console):
    """Display generation results in a nice format."""
    # Summary panel
    success_icon = "[green]✓[/green]" if result.success else "[red]✗[/red]"
    summary_text = (
        f"{success_icon} Generation {'succeeded' if result.success else 'failed'}\n"
        f"Duration: {result.metadata.get('duration_seconds', 0):.2f}s\n"
        f"Total patches: {len(result.patches)}\n"
        f"Applicable patches: {result.metadata.get('num_applicable', 0)}\n"
    )
    
    console.print(Panel(summary_text, title="Results", border_style="green" if result.success else "red"))
    
    # Patches table
    if result.patches:
        table = Table(title="Generated Patches")
        table.add_column("File", style="cyan")
        table.add_column("Valid", justify="center")
        table.add_column("Risk", justify="right", style="yellow")
        table.add_column("Changes", justify="right", style="blue")
        table.add_column("Status")
        
        for patch in result.patches:
            file_name = Path(patch.file_path).name
            valid = "[green]✓[/green]" if patch.is_valid_syntax else "[red]✗[/red]"
            risk = f"{patch.risk_score():.2f}"
            
            # Count changes
            lines = [l for l in patch.unified_diff.split('\n') if l.startswith(('+', '-'))]
            changes = f"{len(lines)} lines"
            
            if patch.can_apply():
                status = "[green]Can apply[/green]"
            else:
                status = f"[red]Errors: {len(patch.validation_errors)}[/red]"
            
            table.add_row(file_name, valid, risk, changes, status)
        
        console.print("\n", table)
    
    # Errors
    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")


def _display_provenance(provenance: dict, console: Console):
    """Display provenance metadata."""
    # Header
    run_id = provenance.get("run_id", "unknown")
    success = provenance.get("success", False)
    success_icon = "[green]✓[/green]" if success else "[red]✗[/red]"
    
    header = (
        f"{success_icon} Run ID: {run_id}\n"
        f"Task: {provenance.get('issue_description', 'N/A')}\n"
        f"Duration: {provenance.get('duration_seconds', 0):.2f}s\n"
        f"Status: {'Success' if success else 'Failed'}"
    )
    
    console.print(Panel(header, title="Provenance Metadata", border_style="blue"))
    
    # Models used
    models = provenance.get("models_used", [])
    if models:
        table = Table(title="Models Used")
        table.add_column("Phase", style="cyan")
        table.add_column("Model", style="yellow")
        table.add_column("Purpose")
        table.add_column("Tokens", justify="right", style="blue")
        table.add_column("Time", justify="right", style="green")
        
        for model in models:
            table.add_row(
                model.get("phase", ""),
                model.get("model_name", ""),
                model.get("purpose", "")[:40],
                str(model.get("tokens_used", 0)),
                f"{model.get('duration_ms', 0):.0f}ms"
            )
        
        console.print("\n", table)
    
    # Safety checks
    checks = provenance.get("safety_checks", [])
    if checks:
        table = Table(title="Safety Checks")
        table.add_column("Type", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details")
        
        for check in checks:
            passed = check.get("passed", False)
            status = "[green]✓[/green]" if passed else "[red]✗[/red]"
            
            table.add_row(
                check.get("check_type", ""),
                status,
                check.get("details", "")[:60]
            )
        
        console.print("\n", table)
    
    # File modifications
    mods = provenance.get("file_modifications", [])
    if mods:
        table = Table(title="File Modifications")
        table.add_column("File", style="cyan")
        table.add_column("Changes", justify="right", style="yellow")
        table.add_column("Backup", style="dim")
        
        for mod in mods:
            file_path = mod.get("file_path", "")
            changes = f"+{mod.get('lines_added', 0)}/-{mod.get('lines_removed', 0)}"
            backup = mod.get("backup_path", "N/A")
            
            table.add_row(Path(file_path).name, changes, Path(backup).name if backup != "N/A" else "N/A")
        
        console.print("\n", table)


if __name__ == "__main__":
    app()
