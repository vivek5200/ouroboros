"""
Context Encoder Implementation
================================

Compresses large code contexts using Jamba-1.5-Mini (Mamba-Transformer hybrid).
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from openai import OpenAI
import ai21

from .config import ContextEncoderConfig, EncoderProvider, get_config
from .validator import ContextIntegrityValidator


class CompressedContext:
    """Represents a compressed context block with metadata."""
    
    def __init__(
        self,
        summary: str,
        file_references: List[str],
        tokens_in: int,
        tokens_out: int,
        compression_ratio: float,
        metadata: Dict[str, Any],
    ):
        self.summary = summary
        self.file_references = file_references
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.compression_ratio = compression_ratio
        self.metadata = metadata
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "summary": self.summary,
            "file_references": self.file_references,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "compression_ratio": self.compression_ratio,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    def checksum(self) -> str:
        """Calculate checksum of the compressed context."""
        content = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class ContextEncoder:
    """
    The Context Encoder (Phase 3: Mamba Layer).
    
    Compresses large codebases using State Space Models (Jamba-1.5-Mini)
    to create dense representations for the Builder.
    
    Architecture:
        GraphRAG Subgraph → Jamba → Compressed Context → Builder
    """
    
    def __init__(self, config: Optional[ContextEncoderConfig] = None):
        """Initialize the context encoder."""
        self.config = config or get_config()
        self.validator = ContextIntegrityValidator(self.config)
        self.client: Optional[Union[OpenAI, ai21.AI21Client]] = None
        
        # Initialize client based on provider
        if self.config.provider in (EncoderProvider.JAMBA_CLOUD, EncoderProvider.JAMBA_LOCAL):
            self._init_jamba_client()
    
    def _init_jamba_client(self) -> None:
        """Initialize Jamba client (AI21 Cloud or LM Studio local)."""
        try:
            jamba_config = self.config.jamba
            
            if jamba_config.use_cloud:
                # AI21 Cloud API - use native AI21 SDK
                if not jamba_config.cloud_api_key:
                    raise ValueError(
                        "AI21_API_KEY environment variable not set. "
                        "Get your API key from: https://studio.ai21.com/account/api-key"
                    )
                
                self.client = ai21.AI21Client(api_key=jamba_config.cloud_api_key)
            else:
                # LM Studio local - use OpenAI-compatible endpoint
                self.client = OpenAI(
                    base_url=jamba_config.local_base_url,
                    api_key="not-needed",  # Local doesn't need API key
                )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Jamba client: {e}")
    
    def compress(
        self,
        codebase_context: str,
        target_files: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CompressedContext:
        """
        Compress a large codebase context into a dense summary.
        
        Args:
            codebase_context: Raw context from GraphRAG (file contents, dependencies)
            target_files: List of file paths being modified
            metadata: Additional metadata (prompt_id, checksum, etc.)
        
        Returns:
            CompressedContext with summary and provenance
        """
        start_time = time.time()
        
        # Build compression prompt
        prompt = self._build_compression_prompt(codebase_context, target_files)
        
        # Call Jamba (cloud or local)
        if self.config.provider in (EncoderProvider.JAMBA_CLOUD, EncoderProvider.JAMBA_LOCAL):
            summary, tokens_in, tokens_out = self._call_jamba(prompt)
        else:  # Mock
            summary, tokens_in, tokens_out = self._mock_compression(prompt)
        
        # Calculate compression ratio
        compression_ratio = tokens_in / max(tokens_out, 1)
        
        # Create compressed context
        compressed = CompressedContext(
            summary=summary,
            file_references=target_files,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            compression_ratio=compression_ratio,
            metadata={
                "model": self.config.model_version,
                "provider": self.config.provider.value,
                "compression_time": time.time() - start_time,
                "compression_strategy": self.config.compression_strategy,
                **(metadata or {}),
            },
        )
        
        # Validate integrity
        validation_result = self.validator.validate(compressed, codebase_context)
        if not validation_result.is_valid:
            raise ValueError(
                f"Context integrity validation failed: {validation_result.errors} "
                f"(score: {validation_result.score}, warnings: {validation_result.warnings})"
            )
        
        return compressed
    
    def _build_compression_prompt(
        self, codebase_context: str, target_files: List[str]
    ) -> str:
        """Build the prompt for context compression."""
        strategy = self.config.compression_strategy
        
        if strategy == "technical_summary":
            return f"""Role: Senior Software Architect

Task: Compress the following codebase context into a high-level technical summary.

Target Files Being Modified:
{chr(10).join(f"- {file}" for file in target_files)}

Codebase Context:
```
{codebase_context}
```

Instructions:
1. Create a dense technical summary (max 4000 tokens)
2. Include:
   - File structure and dependencies
   - Key classes, functions, and their signatures
   - Import relationships
   - Type definitions and interfaces
3. Format as structured documentation
4. Reference specific file names explicitly
5. Do NOT generate code - only describe structure

Output Format:
# Technical Summary

## File Structure
[List files and their purposes]

## Dependencies
[Map import relationships]

## Key Components
[Document classes/functions with signatures]

## Type Definitions
[List interfaces and types]
"""
        else:  # pseudo_code
            return f"""Role: Code Architect

Task: Generate pseudo-code headers representing the codebase structure.

Target Files: {', '.join(target_files)}

Context:
```
{codebase_context}
```

Output pseudo-code headers (TypeScript/Python style) with:
- All function signatures
- Class definitions
- Type annotations
- Import statements
- NO implementation code
"""
    
    def _call_jamba(self, prompt: str) -> tuple[str, int, int]:
        """Call Jamba-1.5-Mini for context compression."""
        if not self.client:
            raise RuntimeError("Jamba client not initialized")
        
        try:
            if self.config.jamba.use_cloud:
                # AI21 Cloud API - use native SDK
                from ai21.models.chat import ChatMessage
                
                response = self.client.chat.completions.create(
                    model=self.config.jamba.model_name,
                    messages=[ChatMessage(role="user", content=prompt)],
                    max_tokens=self.config.jamba.max_output_tokens,
                    temperature=self.config.jamba.temperature,
                )
                
                summary = response.choices[0].message.content
                # AI21 doesn't return token counts in the same way, estimate them
                tokens_in = len(prompt) // 4  # Rough estimate: 4 chars per token
                tokens_out = len(summary) // 4
            else:
                # LM Studio local - use OpenAI-compatible API
                response = self.client.chat.completions.create(
                    model=self.config.jamba.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.config.jamba.max_output_tokens,
                    temperature=self.config.jamba.temperature,
                )
                
                summary = response.choices[0].message.content
                tokens_in = response.usage.prompt_tokens
                tokens_out = response.usage.completion_tokens
            
            return summary, tokens_in, tokens_out
        
        except Exception as e:
            raise RuntimeError(f"Jamba API call failed: {e}")
    
    def _mock_compression(self, prompt: str) -> tuple[str, int, int]:
        """Mock compression for testing without API calls."""
        # Extract target files from prompt
        import re
        file_matches = re.findall(r'([a-zA-Z0-9_/]+\.(?:ts|js|py|tsx|jsx))', prompt)
        
        files_section = "\n".join(f"- {file}" for file in file_matches[:5])
        
        summary = f"""# Technical Summary (Mock)

## File Structure
{files_section if files_section else "- No files detected"}

## Dependencies
- Import relationships analyzed
- Dependencies mapped

## Key Components
- Functions and classes extracted: {len(file_matches)} files processed
- Type signatures preserved
- Method implementations documented

## Compression Stats
- Input: ~{len(prompt)} characters
- Compression ratio: ~10:1
- Files referenced: {', '.join(file_matches[:3]) if file_matches else 'none'}
"""
        return summary, len(prompt) // 4, len(summary) // 4
