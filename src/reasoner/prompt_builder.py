"""
Prompt engineering system for refactor plan generation.

Converts graph context (from ContextSerializer) into structured prompts
that guide the LLM to generate valid RefactorPlan JSON. Includes system
prompts, few-shot examples, and task-specific templates.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from src.librarian.context_serializer import CompressedContextBlock


# ===== System Prompts =====

SYSTEM_PROMPT_BASE = """You are an expert software architect and refactoring specialist. Your role is to analyze codebases and generate precise, executable RefactorPlan JSON objects.

⚠️ CRITICAL: Your response MUST be ONLY valid JSON. No markdown, no code fences, no explanations.
⚠️ CRITICAL: All fields must use proper JSON types - arrays of OBJECTS, not arrays of STRINGS.

You will receive:
1. **Task Description**: The refactoring goal (e.g., "Rename function foo to bar")
2. **Codebase Context**: Structural information about relevant files, classes, and functions
3. **Dependency Graph**: Relationships between code elements (imports, calls, inheritance)

Your output MUST be a valid RefactorPlan JSON object matching this EXACT schema:

```json
{
  "plan_id": "unique_identifier",
  "description": "Human-readable summary of the refactor",
  "primary_changes": [
    {
      "target_file": "path/to/file.py",
      "operation": "create|modify|delete|rename|move|extract|inline",
      "change_type": "import|class|function|method|variable|parameter",
      "start_line": 10,
      "end_line": 20,
      "old_content": "original code (for modify/delete/rename)",
      "new_content": "replacement code (for create/modify/rename)",
      "symbol_name": "current_name",
      "new_symbol_name": "new_name (for rename operations)"
    }
  ],
  "dependency_impacts": [
    {
      "affected_file": "path/to/dependent.py",
      "impact_type": "call|inheritance|import|type_usage",
      "required_changes": [
        {
          "target_file": "path/to/dependent.py",
          "operation": "modify",
          "change_type": "function",
          "start_line": 45,
          "end_line": 45,
          "old_content": "old_function_call()",
          "new_content": "new_function_call()"
        }
      ],
      "breaking_change": true|false
    }
  ],
  "execution_order": [0, 1, 2],
  "risk_level": "low|medium|high|critical",
  "estimated_files_affected": 5
}
```

**Critical Rules:**
1. ALWAYS output valid JSON - no markdown code fences, no explanations outside JSON
2. Use EXACT file paths from the context (no assumptions)
3. Specify precise line numbers for changes
4. Include ALL affected files in dependency_impacts
5. Order changes in execution_order to avoid breaking dependencies
6. Be conservative with risk_level - mark as "high" if uncertain
7. ⚠️ NEVER use string arrays like ["Update call..."] - ALWAYS use object arrays with full FileChange objects
8. ⚠️ Every item in required_changes MUST be a complete FileChange object with all required fields

**Refactor Operations:**
- `create`: Add new code element
- `modify`: Change existing code in-place
- `delete`: Remove code element
- `rename`: Change symbol name (requires updating all references)
- `move`: Relocate code to different file/class
- `extract`: Split code into separate function/class
- `inline`: Merge code into caller

**Risk Assessment:**
- `low`: Simple rename, add import, isolated change
- `medium`: Modify function signature, change class structure
- `high`: Move code across files, complex refactor affecting multiple modules
- `critical`: Breaking API changes, architectural shifts, public interface modifications
"""

SYSTEM_PROMPT_RENAME = """Additional guidance for RENAME operations:

When renaming a symbol (function, class, variable):
1. Primary change: Update the definition in target_file
2. Dependency impacts: Identify ALL files that reference the symbol
3. For each dependent file:
   - Specify impact_type as "call" (functions), "inheritance" (classes), or "import"
   - Add required_changes as array of FileChange OBJECTS (not strings)
   - Each change must have: target_file, operation, change_type, start_line, end_line, old_content, new_content
   - Mark breaking_change=true if external API is affected

⚠️ WRONG FORMAT (string array):
"required_changes": ["Update call to new_name()"]

✅ CORRECT FORMAT (object array):
"required_changes": [
  {
    "target_file": "main.py",
    "operation": "modify",
    "change_type": "function",
    "start_line": 45,
    "end_line": 45,
    "old_content": "old_function_call()",
    "new_content": "new_function_call()"
  }
]

Example for renaming function `calculate_sum` to `compute_total`:
- Primary change in math_utils.py: operation="rename", symbol_name="calculate_sum", new_symbol_name="compute_total"
- Dependency impact in main.py: Full FileChange object with line numbers and content
- Dependency impact in __init__.py: Full FileChange object for import statement
"""

SYSTEM_PROMPT_EXTRACT = """Additional guidance for EXTRACT operations:

When extracting code into a new function/class:
1. Create new symbol with operation="create"
2. Modify original location with operation="modify" to call new symbol
3. Add import if extraction crosses file boundaries
4. Update dependency graph:
   - Original callers now indirectly call extracted code
   - May reduce coupling if well-designed

Example for extracting validation logic into validate_input():
- Create validate_input() function: operation="create", change_type="function"
- Modify original function: Replace validation code with validate_input() call
- Update execution_order: [0, 1] (create first, then modify)
"""

# ===== Few-Shot Examples =====

FEW_SHOT_RENAME_FUNCTION = """
**Example Task:** Rename function `process_data` to `transform_data` in data_processor.py

**Context:**
# File: data_processor.py
**Language:** python

## Functions
- `process_data`
  - Signature: `process_data(input: List[str]) -> List[str]`

## Imports
- → `utils.py`

**Dependency Graph:**
- main.py CALLS process_data (line 45)
- test_processor.py CALLS process_data (line 12, 23)

**Output:**
```json
{
  "plan_id": "rename_process_data_001",
  "description": "Rename function process_data to transform_data in data_processor.py and update all call sites",
  "primary_changes": [
    {
      "target_file": "data_processor.py",
      "operation": "rename",
      "change_type": "function",
      "start_line": 15,
      "end_line": 20,
      "old_content": "def process_data(input: List[str]) -> List[str]:",
      "new_content": "def transform_data(input: List[str]) -> List[str]:",
      "symbol_name": "process_data",
      "new_symbol_name": "transform_data"
    }
  ],
  "dependency_impacts": [
    {
      "affected_file": "main.py",
      "impact_type": "call",
      "required_changes": [
        {
          "target_file": "main.py",
          "operation": "modify",
          "change_type": "function",
          "start_line": 45,
          "end_line": 45,
          "old_content": "result = process_data(data)",
          "new_content": "result = transform_data(data)",
          "symbol_name": "process_data",
          "new_symbol_name": "transform_data"
        }
      ],
      "breaking_change": false
    },
    {
      "affected_file": "test_processor.py",
      "impact_type": "call",
      "required_changes": [
        {
          "target_file": "test_processor.py",
          "operation": "modify",
          "change_type": "function",
          "start_line": 12,
          "end_line": 12,
          "old_content": "output = process_data(sample)",
          "new_content": "output = transform_data(sample)"
        },
        {
          "target_file": "test_processor.py",
          "operation": "modify",
          "change_type": "function",
          "start_line": 23,
          "end_line": 23,
          "old_content": "result = process_data(test_input)",
          "new_content": "result = transform_data(test_input)"
        }
      ],
      "breaking_change": false
    }
  ],
  "execution_order": [0],
  "risk_level": "low",
  "estimated_files_affected": 3
}
```
"""

FEW_SHOT_EXTRACT_FUNCTION = """
**Example Task:** Extract validation logic from process_order() into a separate validate_order() function

**Context:**
# File: order_service.py
**Language:** python

## Functions
- `process_order`
  - Signature: `process_order(order: Order) -> bool`
  - Lines 50-80
  - Contains inline validation logic (lines 55-65)

**Output:**
```json
{
  "plan_id": "extract_validation_001",
  "description": "Extract order validation logic from process_order into a new validate_order function",
  "primary_changes": [
    {
      "target_file": "order_service.py",
      "operation": "create",
      "change_type": "function",
      "start_line": 45,
      "end_line": 45,
      "new_content": "def validate_order(order: Order) -> bool:\\n    if not order.items:\\n        return False\\n    if order.total <= 0:\\n        return False\\n    return True",
      "symbol_name": "validate_order"
    },
    {
      "target_file": "order_service.py",
      "operation": "modify",
      "change_type": "function",
      "start_line": 55,
      "end_line": 65,
      "old_content": "    if not order.items:\\n        return False\\n    if order.total <= 0:\\n        return False",
      "new_content": "    if not validate_order(order):\\n        return False",
      "symbol_name": "process_order"
    }
  ],
  "dependency_impacts": [],
  "execution_order": [0, 1],
  "risk_level": "low",
  "estimated_files_affected": 1
}
```
"""


class PromptBuilder:
    """
    Builds structured prompts for refactor plan generation.
    
    Takes serialized context from ContextSerializer and task descriptions,
    then constructs prompts optimized for each LLM provider.
    """
    
    def __init__(self, include_examples: bool = True):
        """
        Initialize prompt builder.
        
        Args:
            include_examples: Whether to include few-shot examples in prompts
        """
        self.include_examples = include_examples
    
    def build_system_prompt(self, operation_type: Optional[str] = None) -> str:
        """
        Build system prompt with optional operation-specific guidance.
        
        Args:
            operation_type: Type of refactor operation (rename, extract, etc.)
        
        Returns:
            Complete system prompt string
        """
        prompt = SYSTEM_PROMPT_BASE
        
        # Add operation-specific guidance
        if operation_type == "rename":
            prompt += "\n\n" + SYSTEM_PROMPT_RENAME
        elif operation_type == "extract":
            prompt += "\n\n" + SYSTEM_PROMPT_EXTRACT
        
        return prompt
    
    def build_user_prompt(
        self,
        task_description: str,
        context_blocks: List[CompressedContextBlock],
        dependency_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build user prompt with task and context.
        
        Args:
            task_description: What the user wants to accomplish
            context_blocks: Serialized context from ContextSerializer
            dependency_info: Optional dependency graph information
        
        Returns:
            Complete user prompt string
        """
        
        lines = []
        
        # Task header
        lines.append("# Refactoring Task")
        lines.append(f"\n{task_description}\n")
        
        # Add examples if enabled
        if self.include_examples:
            lines.append("\n# Examples")
            lines.append(FEW_SHOT_RENAME_FUNCTION)
        
        # Codebase context
        lines.append("\n# Codebase Context")
        lines.append("\nRelevant files and their structure:\n")
        
        for block in context_blocks:
            # block_id contains the file path for file-level blocks
            file_name = Path(block.block_id).name if block.block_type == "file" else block.block_id
            lines.append(f"\n## {file_name}")
            lines.append(f"Token count: {block.token_count}\n")
            lines.append(block.content)
            lines.append("\n---\n")
        
        # Dependency information
        if dependency_info:
            lines.append("\n# Dependency Graph")
            lines.append("\nRelationships between code elements:\n")
            lines.append(self._format_dependencies(dependency_info))
        
        # Output instruction
        lines.append("\n# Your Task")
        lines.append("\nGenerate a complete RefactorPlan JSON object for the task above.")
        lines.append("Output ONLY the JSON - no markdown fences, no explanations.")
        
        return "\n".join(lines)
    
    def _format_dependencies(self, dependency_info: Dict[str, Any]) -> str:
        """Format dependency information for prompt."""
        lines = []
        
        if "calls" in dependency_info:
            lines.append("\n**Function Calls:**")
            for caller, callees in dependency_info["calls"].items():
                lines.append(f"- {caller} calls: {', '.join(callees)}")
        
        if "imports" in dependency_info:
            lines.append("\n**Imports:**")
            for file, imports in dependency_info["imports"].items():
                lines.append(f"- {file} imports: {', '.join(imports)}")
        
        if "inheritance" in dependency_info:
            lines.append("\n**Inheritance:**")
            for child, parents in dependency_info["inheritance"].items():
                lines.append(f"- {child} extends: {', '.join(parents)}")
        
        return "\n".join(lines)
    
    def estimate_prompt_tokens(self, system_prompt: str, user_prompt: str) -> int:
        """
        Estimate total tokens for prompt.
        
        Uses tiktoken for approximation.
        """
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            total_tokens = len(encoding.encode(system_prompt + user_prompt))
            return total_tokens
        except ImportError:
            # Fallback: 1 token ~= 4 characters
            return (len(system_prompt) + len(user_prompt)) // 4
