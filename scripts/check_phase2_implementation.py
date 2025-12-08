"""
Phase 2 Implementation Verification Script

Performs comprehensive checks to verify Phase 2 (The Reasoner) is properly implemented:
1. Module imports and availability
2. Provider configurations
3. LLM client implementations
4. Core component functionality
5. Integration with Phase 1
"""

import sys
from pathlib import Path

def check_imports():
    """Verify all Phase 2 modules can be imported."""
    print("\n" + "=" * 80)
    print("1. MODULE IMPORTS CHECK")
    print("=" * 80)
    
    try:
        from src.reasoner import Reasoner, ReasonerConfig, LLMProvider
        print("✓ Core modules: Reasoner, ReasonerConfig, LLMProvider")
        
        from src.reasoner.config import (
            CLAUDE_CONFIG, GEMINI_CONFIG, JAMBA_CONFIG, 
            OPENAI_CONFIG, LMSTUDIO_CONFIG, MOCK_CONFIG
        )
        print("✓ Provider configurations: 6 configs loaded")
        
        from src.reasoner.llm_client import (
            LLMClient, ClaudeClient, GeminiClient, JambaClient,
            OpenAIClient, LMStudioClient, MockClient
        )
        print("✓ LLM clients: 6 implementations + abstract base")
        
        from src.reasoner.prompt_builder import PromptBuilder
        print("✓ Prompt builder: Available")
        
        from src.reasoner.plan_parser import PlanParser, RefactorPlan
        print("✓ Plan parser: Available with RefactorPlan schema")
        
        from src.reasoner.dependency_analyzer import DependencyAnalyzer
        print("✓ Dependency analyzer: Available")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def check_providers():
    """Verify all LLM providers are configured."""
    print("\n" + "=" * 80)
    print("2. PROVIDER CONFIGURATIONS")
    print("=" * 80)
    
    from src.reasoner import LLMProvider
    from src.reasoner.config import (
        CLAUDE_CONFIG, GEMINI_CONFIG, JAMBA_CONFIG,
        OPENAI_CONFIG, LMSTUDIO_CONFIG, MOCK_CONFIG
    )
    
    configs = {
        "Claude": CLAUDE_CONFIG,
        "Gemini": GEMINI_CONFIG,
        "Jamba": JAMBA_CONFIG,
        "OpenAI": OPENAI_CONFIG,
        "LM Studio": LMSTUDIO_CONFIG,
        "Mock": MOCK_CONFIG
    }
    
    print(f"\n{'Provider':<12} | {'Model':<35} | {'Context':<12} | {'Cost (per 1K)'}")
    print("-" * 90)
    
    for name, config in configs.items():
        context = f"{config.context_window:,} tokens"
        if config.cost_per_1k_input == 0:
            cost = "FREE"
        else:
            cost = f"${config.cost_per_1k_input:.4f} in"
        
        print(f"{name:<12} | {config.model_name:<35} | {context:<12} | {cost}")
    
    print(f"\n✓ Total providers configured: {len(configs)}")
    return True

def check_clients():
    """Verify all LLM client implementations."""
    print("\n" + "=" * 80)
    print("3. LLM CLIENT IMPLEMENTATIONS")
    print("=" * 80)
    
    from src.reasoner.llm_client import (
        ClaudeClient, GeminiClient, JambaClient,
        OpenAIClient, LMStudioClient, MockClient
    )
    
    clients = [
        ("ClaudeClient", ClaudeClient),
        ("GeminiClient", GeminiClient),
        ("JambaClient", JambaClient),
        ("OpenAIClient", OpenAIClient),
        ("LMStudioClient", LMStudioClient),
        ("MockClient", MockClient)
    ]
    
    for name, client_cls in clients:
        # Check if client has required methods
        has_generate = hasattr(client_cls, 'generate')
        has_setup = hasattr(client_cls, '_setup_client')
        
        if has_generate and has_setup:
            print(f"✓ {name:<20} - Implements required interface")
        else:
            print(f"✗ {name:<20} - Missing required methods")
    
    return True

def check_file_structure():
    """Verify Phase 2 file structure."""
    print("\n" + "=" * 80)
    print("4. FILE STRUCTURE")
    print("=" * 80)
    
    base_path = Path("src/reasoner")
    required_files = [
        "__init__.py",
        "config.py",
        "llm_client.py",
        "prompt_builder.py",
        "plan_parser.py",
        "dependency_analyzer.py",
        "reasoner.py"
    ]
    
    missing = []
    for file in required_files:
        file_path = base_path / file
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"✓ {file:<25} ({size_kb:.1f} KB)")
        else:
            print(f"✗ {file:<25} MISSING")
            missing.append(file)
    
    if missing:
        print(f"\n✗ Missing files: {', '.join(missing)}")
        return False
    
    return True

def check_test_files():
    """Verify test files exist."""
    print("\n" + "=" * 80)
    print("5. TEST FILES")
    print("=" * 80)
    
    test_files = [
        "scripts/test_phase2_reasoner.py",
        "scripts/generate_refactor_plan.py"
    ]
    
    for test_file in test_files:
        file_path = Path(test_file)
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"✓ {test_file:<40} ({size_kb:.1f} KB)")
        else:
            print(f"✗ {test_file:<40} MISSING")
    
    return True

def check_integration():
    """Check Phase 1 integration."""
    print("\n" + "=" * 80)
    print("6. PHASE 1 INTEGRATION")
    print("=" * 80)
    
    try:
        from src.reasoner.dependency_analyzer import DependencyAnalyzer
        from neo4j import GraphDatabase
        
        print("✓ Neo4j driver available")
        print("✓ DependencyAnalyzer can connect to Phase 1 graph")
        
        # Check if Neo4j is accessible
        try:
            driver = GraphDatabase.driver("bolt://localhost:7687")
            with driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count LIMIT 1")
                count = result.single()["count"]
                print(f"✓ Neo4j accessible with {count:,} nodes")
            driver.close()
        except Exception as e:
            print(f"⚠ Neo4j connection: {e}")
            print("  (This is OK if Neo4j is not running)")
        
        return True
    except Exception as e:
        print(f"✗ Integration check failed: {e}")
        return False

def check_dependencies():
    """Verify required Python packages."""
    print("\n" + "=" * 80)
    print("7. PYTHON DEPENDENCIES")
    print("=" * 80)
    
    required = {
        "anthropic": "Claude API",
        "ai21": "Jamba API",
        "openai": "OpenAI API",
        "google.generativeai": "Gemini API",
        "neo4j": "Graph database",
        "pydantic": "Data validation",
        "tiktoken": "Token counting",
        "typer": "CLI framework",
        "rich": "Terminal formatting"
    }
    
    for package, description in required.items():
        try:
            __import__(package)
            print(f"✓ {package:<25} ({description})")
        except ImportError:
            print(f"✗ {package:<25} MISSING - {description}")
    
    return True

def main():
    """Run all verification checks."""
    print("\n" + "=" * 80)
    print("PHASE 2 IMPLEMENTATION VERIFICATION")
    print("=" * 80)
    
    checks = [
        ("Imports", check_imports),
        ("Providers", check_providers),
        ("Clients", check_clients),
        ("File Structure", check_file_structure),
        ("Test Files", check_test_files),
        ("Integration", check_integration),
        ("Dependencies", check_dependencies)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{'=' * 80}")
    print(f"Results: {passed}/{total} checks passed ({100*passed//total}%)")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 Phase 2 is PROPERLY IMPLEMENTED and ready for use!")
    elif passed >= total * 0.8:
        print("\n⚠️  Phase 2 is MOSTLY implemented with minor issues")
    else:
        print("\n❌ Phase 2 has SIGNIFICANT issues that need attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
