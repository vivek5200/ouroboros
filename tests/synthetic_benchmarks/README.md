# Synthetic Test Suite - Benchmark Refactors

This directory contains 10 canned refactoring scenarios to test the Ouroboros system's ability to track code changes through the graph database.

## Benchmark Structure

Each benchmark follows this pattern:
```
benchmark_name/
├── before/          # Original code state
├── after/           # Expected refactored state
├── test.py          # Validation script
└── README.md        # Description and metrics
```

## Refactoring Scenarios

1. **rename_import** - Change import statement names
2. **move_function** - Relocate function between files
3. **change_signature** - Modify function parameters
4. **extract_class** - Create new class from methods
5. **inline_function** - Remove function indirection
6. **rename_variable** - Update variable references
7. **change_parameter** - Modify parameter names/types
8. **add_method** - Insert new class method
9. **remove_method** - Delete class method
10. **refactor_conditional** - Simplify control flow

## Validation Metrics

Each benchmark is validated against:
- ✅ **compiles**: Code syntax is valid
- ✅ **tests_pass**: Functional behavior preserved
- ✅ **graph_consistent**: Neo4j graph reflects changes correctly
- ✅ **human_audit**: Manual review confirms correctness
