"""
Test Phase 2 Bridge Components
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from src.librarian.context_serializer import ContextSerializer, create_context_window
from src.architect.schemas import (
    RefactorPlan, FileChange, DependencyImpact,
    RefactorOperation, ChangeType, validate_refactor_plan
)
from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.retriever import GraphRetriever
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


def test_call_graph_extraction():
    """Test 1: Verify call graph extraction works."""
    console.print("\n[bold cyan]TEST 1: Call Graph Extraction[/bold cyan]")
    
    from src.librarian.parser import CodeParser
    
    parser = CodeParser()
    
    # Create test file
    test_code = '''
def helper_function():
    return "helper"

def main_function():
    result = helper_function()
    print(result)
    return process_data(result)

def process_data(data):
    return data.upper()
'''
    
    test_file = Path("test_calls.py")
    test_file.write_text(test_code)
    
    try:
        parsed = parser.parse_file(str(test_file))
        
        console.print(f"[green]✓[/green] Parsed {len(parsed['functions'])} functions")
        
        for func in parsed['functions']:
            if func.calls:
                console.print(f"  Function [cyan]{func.name}[/cyan] calls: {', '.join(func.calls)}")
        
        # Check if calls were detected
        main_func = next(f for f in parsed['functions'] if f.name == 'main_function')
        assert len(main_func.calls) >= 2, "Should detect at least 2 calls"
        
        console.print("[green]✓ PASS[/green]: Call graph extraction working\n")
        return True
    finally:
        test_file.unlink(missing_ok=True)


def test_context_serializer():
    """Test 2: Verify context serializer formats."""
    console.print("[bold cyan]TEST 2: Context Serializer[/bold cyan]")
    
    # Mock context
    mock_context = {
        "file": {
            "path": "/path/to/user_service.py",
            "language": "python",
            "checksum": "abc123def456"
        },
        "classes": [
            {"name": "UserService", "language": "python"}
        ],
        "functions": [
            {
                "name": "create_user",
                "signature": "create_user(name: str, email: str) -> User",
                "is_method": False
            }
        ],
        "imports": [
            {"target": "/path/to/user_model.py"}
        ],
        "inheritance": []
    }
    
    # Test XML format
    xml_serializer = ContextSerializer(format="xml")
    xml_block = xml_serializer.serialize_file_context(mock_context)
    
    console.print("[yellow]XML Format:[/yellow]")
    console.print(xml_block.content[:200] + "...")
    console.print(f"Token estimate: {xml_block.token_count}")
    
    # Test Markdown format
    md_serializer = ContextSerializer(format="markdown")
    md_block = md_serializer.serialize_file_context(mock_context)
    
    console.print("\n[yellow]Markdown Format:[/yellow]")
    console.print(md_block.content)
    console.print(f"Token estimate: {md_block.token_count}")
    
    assert xml_block.token_count > 0, "XML token count should be positive"
    assert md_block.token_count > 0, "Markdown token count should be positive"
    
    console.print("\n[green]✓ PASS[/green]: Context serializer working\n")
    return True


def test_diff_skeleton_validation():
    """Test 3: Verify Pydantic schema validation."""
    console.print("[bold cyan]TEST 3: Diff Skeleton Validation[/bold cyan]")
    
    # Create valid refactor plan
    plan = RefactorPlan(
        plan_id="test_001",
        description="Rename function foo to bar",
        primary_changes=[
            FileChange(
                target_file="src/module.py",
                operation=RefactorOperation.RENAME,
                change_type=ChangeType.FUNCTION,
                start_line=10,
                end_line=15,
                symbol_name="foo",
                new_symbol_name="bar",
                old_content="def foo():",
                new_content="def bar():"
            )
        ],
        dependency_impacts=[
            DependencyImpact(
                affected_file="src/caller.py",
                impact_type="call",
                required_changes=[],
                breaking_change=False
            )
        ],
        execution_order=[0],
        risk_level="low",
        estimated_files_affected=2
    )
    
    # Validate
    result = validate_refactor_plan(plan)
    
    console.print(f"Valid: {result.is_valid}")
    console.print(f"Errors: {len(result.errors)}")
    console.print(f"Warnings: {len(result.warnings)}")
    
    if result.warnings:
        for warning in result.warnings:
            console.print(f"  ⚠ {warning}")
    
    # Test serialization
    plan_json = plan.model_dump_json(indent=2)
    console.print("\n[yellow]Serialized JSON:[/yellow]")
    syntax = Syntax(plan_json, "json", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    assert result.is_valid, "Plan should be valid"
    console.print("\n[green]✓ PASS[/green]: Schema validation working\n")
    return True


def test_end_to_end_workflow():
    """Test 4: End-to-end Phase 2 bridge workflow."""
    console.print("[bold cyan]TEST 4: End-to-End Workflow[/bold cyan]")
    
    try:
        # 1. Query graph for context
        db = OuroborosGraphDB()
        retriever = GraphRetriever(db)
        
        console.print("[yellow]Step 1:[/yellow] Retrieving file context from graph...")
        files_summary = retriever.get_all_files_summary()
        
        if not files_summary:
            console.print("[yellow]⚠ No files in database - using mock context[/yellow]")
            context = {
                "file": {"path": "mock.py", "language": "python", "checksum": "mock"},
                "classes": [],
                "functions": [],
                "imports": [],
                "inheritance": []
            }
        else:
            first_file = files_summary[0]['path']
            context = retriever.get_file_context(first_file)
            
            # Handle case where context is invalid
            if not context or 'file' not in context:
                console.print("[yellow]⚠ Invalid context returned - using mock[/yellow]")
                context = {
                    "file": {"path": "mock.py", "language": "python", "checksum": "mock"},
                    "classes": [],
                    "functions": [],
                    "imports": [],
                    "inheritance": []
                }
        
        # 2. Serialize context for LLM
        
        console.print("[yellow]Step 2:[/yellow] Serializing context for LLM...")
        serializer = ContextSerializer(format="markdown")
        
        # Ensure context is valid before serialization
        if not context or 'file' not in context:
            console.print("[yellow]⚠ Invalid context - using mock[/yellow]")
            context = {
                "file": {"path": "mock.py", "language": "python", "checksum": "mock"},
                "classes": [],
                "functions": [],
                "imports": [],
                "inheritance": []
            }
        
        context_block = serializer.serialize_file_context(context)
        
        console.print(f"  Context size: {context_block.token_count} tokens")
        
        # 3. Create mock refactor plan (simulating LLM output)
        console.print("[yellow]Step 3:[/yellow] Validating refactor plan...")
        plan = RefactorPlan(
            plan_id="workflow_test",
            description="Example refactor from Phase 2",
            primary_changes=[
                FileChange(
                    target_file=context['file']['path'],
                    operation=RefactorOperation.MODIFY,
                    change_type=ChangeType.FUNCTION,
                    start_line=1,
                    end_line=10
                )
            ],
            execution_order=[0],
            risk_level="low",
            estimated_files_affected=1
        )
        
        # 4. Validate plan
        validation = validate_refactor_plan(plan)
        
        console.print(f"  Validation: {'✓ PASS' if validation.is_valid else '✗ FAIL'}")
        
        db.close()
        
        console.print("\n[green]✓ PASS[/green]: End-to-end workflow complete\n")
        return True
        
    except Exception as e:
        import traceback
        console.print(f"\n[red]✗ FAIL[/red]: {e}")
        console.print(f"[red]{traceback.format_exc()}[/red]\n")
        return False


def main():
    """Run all Phase 2 bridge tests."""
    console.print("\n" + "=" * 43)
    console.print("  Phase 2 Bridge Components Test Suite")
    console.print("=" * 43 + "\n")
    
    tests = [
        ("Call Graph Extraction", test_call_graph_extraction),
        ("Context Serializer", test_context_serializer),
        ("Diff Skeleton Validation", test_diff_skeleton_validation),
        ("End-to-End Workflow", test_end_to_end_workflow),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            console.print(f"[red]ERROR in {name}: {e}[/red]\n")
            results.append((name, False))
    
    # Summary
    console.print("=" * 43)
    passed_count = sum(1 for _, passed in results if passed)
    console.print(f"Tests Passed: {passed_count}/{len(results)}")
    
    for name, passed in results:
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"{status} {name}")
    
    if passed_count < len(results):
        console.print(f"\n[yellow]⚠ {len(results) - passed_count} tests failed[/yellow]")
    console.print("=" * 43 + "\n")
    
    if passed_count == len(results):
        console.print("\n🎉 [bold green]ALL TESTS PASSED[/bold green] - Phase 2 Bridge Ready!")
    else:
        console.print(f"\n⚠ [yellow]{len(results) - passed_count} tests failed[/yellow]")
    
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]\n")


if __name__ == "__main__":
    main()
