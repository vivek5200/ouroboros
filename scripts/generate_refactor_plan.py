"""
CLI tool to generate refactor plans using Phase 2 Reasoner.

Usage:
    python scripts/generate_refactor_plan.py "Rename function foo to bar" --file src/module.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
import json

from src.reasoner import Reasoner, ReasonerConfig, LLMProvider
from src.architect.schemas import RefactorPlan


app = typer.Typer()
console = Console()


@app.command()
def generate(
    task: str = typer.Argument(..., help="Refactoring task description"),
    file: str = typer.Option(None, "--file", "-f", help="Target file to refactor"),
    symbol: str = typer.Option(None, "--symbol", "-s", help="Target symbol (function/class name)"),
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM provider (openai/claude/jamba/mock)"),
    estimate_only: bool = typer.Option(False, "--estimate", "-e", help="Only estimate cost, don't generate"),
    output: str = typer.Option(None, "--output", "-o", help="Save plan to JSON file"),
):
    """
    Generate a refactor plan using LLM reasoning.
    
    Examples:
        python scripts/generate_refactor_plan.py "Rename function foo to bar" -f src/utils.py
        python scripts/generate_refactor_plan.py "Extract validation logic" -s process_order -f src/orders.py
        python scripts/generate_refactor_plan.py "Move class User to models.py" --estimate
    """
    
    console.print(Panel.fit(
        f"[bold cyan]Phase 2: The Reasoner[/bold cyan]\n"
        f"Task: {task}",
        border_style="cyan"
    ))
    
    # Create config
    provider_enum = LLMProvider(provider.lower())
    config = ReasonerConfig(provider=provider_enum)
    
    console.print(f"\n✓ Provider: [green]{config.provider.value}[/green]")
    console.print(f"✓ Model: [green]{config.model_config.model_name}[/green]")
    console.print(f"✓ Context window: [green]{config.model_config.context_window:,}[/green] tokens\n")
    
    # Initialize reasoner
    try:
        reasoner = Reasoner(config)
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize reasoner: {e}[/red]")
        console.print(f"\n[yellow]Hint:[/yellow] Set your API key:")
        console.print(f"  $env:OPENAI_API_KEY = 'your-key'")
        sys.exit(1)
    
    # Estimate cost first
    try:
        with console.status("[cyan]Estimating cost...[/cyan]"):
            cost_info = reasoner.estimate_cost(
                task_description=task,
                target_file=file,
            )
        
        # Show cost estimate
        cost_table = Table(title="Cost Estimate")
        cost_table.add_column("Metric", style="cyan")
        cost_table.add_column("Value", style="green")
        
        cost_table.add_row("Input tokens", f"{cost_info['input_tokens']:,}")
        cost_table.add_row("Output tokens", f"~{cost_info['output_tokens']:,}")
        cost_table.add_row("Total tokens", f"{cost_info['total_tokens']:,}")
        cost_table.add_row("Estimated cost", f"${cost_info['estimated_cost_usd']:.4f}")
        
        console.print(cost_table)
        
        if estimate_only:
            console.print("\n[green]✓ Cost estimation complete[/green]")
            reasoner.close()
            return
        
    except Exception as e:
        console.print(f"[yellow]⚠ Could not estimate cost: {e}[/yellow]")
    
    # Generate plan
    console.print("\n[cyan]Generating refactor plan with LLM...[/cyan]")
    
    try:
        with console.status(f"[cyan]Querying {config.provider.value}...[/cyan]"):
            plan = reasoner.generate_refactor_plan(
                task_description=task,
                target_file=file,
                target_symbol=symbol,
            )
        
        console.print("\n[green]✓ RefactorPlan generated successfully![/green]\n")
        
        # Display plan
        console.print(Panel(
            f"[bold]Plan ID:[/bold] {plan.plan_id}\n"
            f"[bold]Description:[/bold] {plan.description}\n"
            f"[bold]Risk Level:[/bold] {plan.risk_level}\n"
            f"[bold]Files Affected:[/bold] {plan.estimated_files_affected}",
            title="Plan Summary",
            border_style="green"
        ))
        
        # Show changes
        if plan.primary_changes:
            changes_table = Table(title=f"Primary Changes ({len(plan.primary_changes)})")
            changes_table.add_column("#", style="dim")
            changes_table.add_column("File", style="cyan")
            changes_table.add_column("Operation", style="yellow")
            changes_table.add_column("Type", style="magenta")
            changes_table.add_column("Lines", style="green")
            
            for idx, change in enumerate(plan.primary_changes):
                changes_table.add_row(
                    str(idx),
                    change.target_file,
                    change.operation.value,
                    change.change_type.value,
                    f"{change.start_line}-{change.end_line}" if change.start_line else "N/A"
                )
            
            console.print(changes_table)
        
        # Show dependency impacts
        if plan.dependency_impacts:
            console.print(f"\n[yellow]⚠ Dependency Impacts: {len(plan.dependency_impacts)} files affected[/yellow]")
            
            for impact in plan.dependency_impacts[:5]:  # Show first 5
                impact_type = impact.impact_type if isinstance(impact.impact_type, str) else impact.impact_type.value
                console.print(f"  • {impact.affected_file} ({impact_type})")
            
            if len(plan.dependency_impacts) > 5:
                console.print(f"  ... and {len(plan.dependency_impacts) - 5} more")
        
        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.write_text(plan.model_dump_json(indent=2))
            console.print(f"\n[green]✓ Saved to {output_path}[/green]")
        else:
            # Show JSON preview
            console.print("\n[dim]JSON Preview:[/dim]")
            json_str = plan.model_dump_json(indent=2)
            syntax = Syntax(json_str[:500] + "\n..." if len(json_str) > 500 else json_str, "json", theme="monokai")
            console.print(syntax)
        
        reasoner.close()
        
    except Exception as e:
        console.print(f"\n[red]✗ Failed to generate plan: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        reasoner.close()
        sys.exit(1)


@app.command()
def test_connection(
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM provider to test"),
):
    """Test connection to LLM provider."""
    
    console.print(f"\n[cyan]Testing connection to {provider}...[/cyan]\n")
    
    provider_enum = LLMProvider(provider.lower())
    config = ReasonerConfig(provider=provider_enum)
    
    try:
        from src.reasoner.llm_client import LLMClientFactory
        
        client = LLMClientFactory.create(config)
        console.print(f"✓ Client created: [green]{type(client).__name__}[/green]")
        
        # Try a simple generation
        response = client.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello, Ouroboros!' in JSON format: {\"message\": \"...\"}",
        )
        
        console.print(f"✓ Response received: [green]{response.output_tokens} tokens[/green]")
        console.print(f"✓ Cost: [green]${response.cost_usd:.4f}[/green]")
        console.print(f"\n[bold green]✓ Connection successful![/bold green]\n")
        
        console.print("Response:")
        console.print(Panel(response.content, border_style="green"))
        
    except Exception as e:
        console.print(f"\n[red]✗ Connection failed: {e}[/red]")
        console.print(f"\n[yellow]Troubleshooting:[/yellow]")
        console.print(f"  1. Check API key is set: $env:{config._get_api_key_for_provider(provider_enum)}")
        console.print(f"  2. Verify API key is valid and has credits")
        console.print(f"  3. Check network connection")
        sys.exit(1)


if __name__ == "__main__":
    app()
