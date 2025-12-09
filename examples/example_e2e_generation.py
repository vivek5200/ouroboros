"""
Example: End-to-End Code Generation with Ouroboros

This example demonstrates the complete Ouroboros pipeline for
AI-assisted code generation and refactoring.

Requirements:
- Neo4j database running with codebase indexed
- AI21 API key (optional - can use mock mode)
- Python 3.10+

Note: These examples show the API structure. To run without a database,
you would need to mock the graph_db component. See tests/test_integration_pipeline.py
for examples of fully mocked execution.

Usage:
    # With real Neo4j database:
    python examples/example_e2e_generation.py
    
    # To run tests with mocks:
    pytest tests/test_integration_pipeline.py -v

Created: 2025-12-10
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ouroboros_pipeline import OuroborosCodeGenerator, GenerationRequest


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("ouroboros_generation.log")
        ]
    )


def example_1_basic_generation():
    """
    Example 1: Basic code generation.
    
    Generate patches for a simple refactoring task.
    """
    print("\n" + "=" * 80)
    print("Example 1: Basic Code Generation")
    print("=" * 80)
    
    # Use mock mode (no database/API required)
    with OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="wrong-password",
        use_mock=True,
        skip_db_init=True,
    ) as generator:
        
        # Generate patches
        result = generator.generate(
            issue_description="Add input validation to user creation functions",
            target_files=["src/services/user_service.py"],
            target_functions=["create_user"],
            config="mock"
        )
        
        # Display results
        print(f"\nGeneration completed:")
        print(f"  Success: {result.success}")
        print(f"  Duration: {result.metadata.get('duration_seconds', 0):.2f}s")
        print(f"  Total patches: {len(result.patches)}")
        print(f"  Applicable: {len(result.get_applicable_patches())}")
        print(f"  High-risk: {len(result.get_high_risk_patches())}")
        
        # Show applicable patches
        for i, patch in enumerate(result.get_applicable_patches(), 1):
            print(f"\nPatch {i}:")
            print(f"  File: {patch.file_path}")
            print(f"  Targets: {patch.refactor_plan.edit_targets}")
            print(f"  Risk score: {patch.risk_score():.2f}")
            print(f"  Valid syntax: {patch.is_valid_syntax}")
            
            if patch.unified_diff:
                print(f"\n  Unified Diff Preview:")
                lines = patch.unified_diff.split('\n')[:10]
                for line in lines:
                    print(f"    {line}")
                total_lines = len(patch.unified_diff.split('\n'))
                if total_lines > 10:
                    print(f"    ... ({total_lines - 10} more lines)")


def example_2_batch_generation():
    """
    Example 2: Batch generation for multiple files.
    
    Generate patches for multiple files with different priorities.
    """
    print("\n" + "=" * 80)
    print("Example 2: Batch Code Generation")
    print("=" * 80)
    
    with OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        use_mock=True,
        skip_db_init=True,
    ) as generator:
        
        # Generate for multiple files
        result = generator.generate(
            issue_description="Optimize database queries by adding caching",
            target_files=[
                "src/services/user_service.py",
                "src/services/post_service.py",
                "src/services/comment_service.py",
            ],
            config="mock",
            max_patches=5  # Limit patches
        )
        
        print(f"\nBatch generation completed:")
        print(f"  Files processed: {len(result.refactor_plans)}")
        print(f"  Patches generated: {len(result.patches)}")
        
        # Group by risk level
        low_risk = [p for p in result.patches if p.risk_score() < 0.3]
        medium_risk = [p for p in result.patches if 0.3 <= p.risk_score() < 0.7]
        high_risk = [p for p in result.patches if p.risk_score() >= 0.7]
        
        print(f"\nRisk distribution:")
        print(f"  Low risk (< 0.3): {len(low_risk)}")
        print(f"  Medium risk (0.3-0.7): {len(medium_risk)}")
        print(f"  High risk (>= 0.7): {len(high_risk)}")


def example_3_safe_application():
    """
    Example 3: Safe patch application with validation.
    
    Apply patches with safety checks and backups.
    """
    print("\n" + "=" * 80)
    print("Example 3: Safe Patch Application")
    print("=" * 80)
    
    with OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        use_mock=True,
        skip_db_init=True,
    ) as generator:
        
        # Generate code
        result = generator.generate(
            issue_description="Add error handling to API endpoints",
            target_files=["src/api/routes.py"],
            config="mock"
        )
        
        # Apply only low-risk patches
        max_risk_threshold = 0.3
        
        print(f"\nApplying patches (max risk: {max_risk_threshold}):")
        
        for patch in result.get_applicable_patches(max_risk=max_risk_threshold):
            print(f"\n  Patch: {patch.file_path}")
            print(f"  Risk: {patch.risk_score():.2f}")
            print(f"  Valid: {patch.is_valid_syntax}")
            
            # Dry run first
            success = generator.apply_patch(patch, dry_run=True)
            
            if success:
                print(f"  ✓ Dry run successful")
                
                # In real scenario, would apply here:
                # generator.apply_patch(patch, backup=True, dry_run=False)
            else:
                print(f"  ✗ Dry run failed")
        
        # Show patches that need review
        high_risk = result.get_high_risk_patches(threshold=max_risk_threshold)
        if high_risk:
            print(f"\n{len(high_risk)} patches need manual review:")
            for patch in high_risk:
                print(f"  - {patch.file_path} (risk: {patch.risk_score():.2f})")


def example_4_config_comparison():
    """
    Example 4: Compare different generation configs.
    
    Show how different configs affect generation quality and speed.
    """
    print("\n" + "=" * 80)
    print("Example 4: Config Comparison")
    print("=" * 80)
    
    configs = ["fast", "balanced", "quality", "mock"]
    
    for config in configs:
        print(f"\n{config.upper()} config:")
        print("-" * 40)
        
        with OuroborosCodeGenerator(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            use_mock=True,
            skip_db_init=True,
        ) as generator:
            
            result = generator.generate(
                issue_description="Refactor authentication logic",
                target_files=["src/auth/auth.py"],
                config=config
            )
            
            print(f"  Duration: {result.metadata.get('duration_seconds', 0):.2f}s")
            print(f"  Patches: {len(result.patches)}")
            print(f"  Applicable: {len(result.get_applicable_patches())}")
            
            if result.patches:
                avg_risk = sum(p.risk_score() for p in result.patches) / len(result.patches)
                print(f"  Avg risk: {avg_risk:.2f}")


def example_5_with_context_encoding():
    """
    Example 5: Generation with context compression.
    
    Shows how Phase 3 (Jamba) compresses context for better generation.
    """
    print("\n" + "=" * 80)
    print("Example 5: With Context Encoding (Jamba)")
    print("=" * 80)
    
    # Note: This requires AI21 API key and real database
    print("\nThis example requires:")
    print("  - AI21 API key (set AI21_API_KEY env var)")
    print("  - Neo4j database with indexed codebase")
    print("  - Real file paths")
    
    # Mock mode for demonstration
    with OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        ai21_api_key="mock_key",  # Would use real key
        use_mock=True,
        skip_db_init=True,
    ) as generator:
        
        result = generator.generate(
            issue_description="Optimize large data processing functions",
            target_files=["src/data/processor.py"],
            context_limit=4096,  # Compress to 4k tokens
            config="mock"
        )
        
        print(f"\nGeneration with context compression:")
        print(f"  Plans: {len(result.refactor_plans)}")
        print(f"  Compressed contexts: {len(result.compressed_contexts)}")
        
        for i, plan in enumerate(result.refactor_plans, 1):
            compression_ratio = plan.context.get("compression_ratio", "N/A")
            print(f"\n  Plan {i}:")
            print(f"    File: {plan.file_path}")
            print(f"    Compression: {compression_ratio}")


def example_6_error_handling():
    """
    Example 6: Error handling and recovery.
    
    Shows how the pipeline handles errors gracefully.
    """
    print("\n" + "=" * 80)
    print("Example 6: Error Handling")
    print("=" * 80)
    
    with OuroborosCodeGenerator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        use_mock=True,
        skip_db_init=True,
    ) as generator:
        
        # Try to generate for non-existent file
        result = generator.generate(
            issue_description="Fix bugs",
            target_files=["nonexistent/file.py"],
            config="mock"
        )
        
        print(f"\nGeneration result:")
        print(f"  Success: {result.success}")
        print(f"  Errors: {len(result.errors)}")
        
        if result.errors:
            print("\n  Error details:")
            for error in result.errors:
                print(f"    - {error}")
        
        # Pipeline continues even with errors
        print(f"\n  Patches generated: {len(result.patches)}")
        print(f"  (Pipeline gracefully handles errors)")


def main():
    """Run all examples."""
    setup_logging()
    
    print("=" * 80)
    print("OUROBOROS END-TO-END CODE GENERATION EXAMPLES")
    print("=" * 80)
    print("\nThese examples demonstrate the complete Ouroboros pipeline:")
    print("  Phase 1: Librarian (Knowledge Graph)")
    print("  Phase 2: Reasoner (Analysis & Planning)")
    print("  Phase 3: Context Encoder (Jamba Compression)")
    print("  Phase 4: Builder (Diffusion Generation)")
    
    try:
        example_1_basic_generation()
        example_2_batch_generation()
        example_3_safe_application()
        example_4_config_comparison()
        example_5_with_context_encoding()
        example_6_error_handling()
        
        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        logging.exception("Example execution failed")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
