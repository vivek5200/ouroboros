"""
Ouroboros - Provenance Metadata Tracker
Utilities for tracking and validating provenance information.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class ProvenanceTracker:
    """
    Tracks and validates provenance metadata for all operations.
    Generates artifact_metadata.json for auditability.
    """
    
    def __init__(self, output_dir: str = "."):
        """
        Initialize provenance tracker.
        
        Args:
            output_dir: Directory to save metadata artifacts
        """
        self.output_dir = Path(output_dir)
        self.operations = []
    
    def log_operation(
        self,
        operation_type: str,
        target: str,
        model_name: str,
        model_version: str,
        prompt_id: str,
        context_checksum: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a provenance operation.
        
        Args:
            operation_type: Type of operation (ingest, refactor, etc.)
            target: Target file/class/function
            model_name: Model component name
            model_version: Model version
            prompt_id: Unique operation identifier
            context_checksum: Content checksum
            metadata: Additional metadata
            
        Returns:
            Logged operation ID
        """
        operation = {
            "operation_id": f"op_{len(self.operations) + 1}",
            "operation_type": operation_type,
            "target": target,
            "model_name": model_name,
            "model_version": model_version,
            "prompt_id": prompt_id,
            "context_checksum": context_checksum,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.operations.append(operation)
        return operation["operation_id"]
    
    def save_artifact(self, filename: str = "artifact_metadata.json"):
        """
        Save all logged operations to JSON artifact.
        
        Args:
            filename: Output filename
        """
        output_path = self.output_dir / filename
        
        artifact = {
            "ouroboros_version": "1.0.0",
            "phase": "Phase 1: The Librarian",
            "generated_at": datetime.utcnow().isoformat(),
            "total_operations": len(self.operations),
            "operations": self.operations
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Provenance artifact saved: {output_path}")
        return output_path
    
    def validate_operation(self, operation: Dict[str, Any]) -> bool:
        """
        Validate that an operation has all required provenance fields.
        
        Args:
            operation: Operation dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "model_name",
            "model_version",
            "prompt_id",
            "timestamp"
        ]
        
        return all(field in operation for field in required_fields)
    
    def get_operation_history(self, target: str) -> list:
        """
        Get all operations performed on a specific target.
        
        Args:
            target: Target file/class/function
            
        Returns:
            List of operations
        """
        return [op for op in self.operations if op["target"] == target]
    
    def clear(self):
        """Clear all logged operations."""
        self.operations = []


def generate_prompt_id(prefix: str = "prompt") -> str:
    """
    Generate a unique prompt ID.
    
    Args:
        prefix: ID prefix
        
    Returns:
        Unique prompt identifier
    """
    timestamp = datetime.utcnow().timestamp()
    return f"{prefix}_{int(timestamp * 1000)}"
