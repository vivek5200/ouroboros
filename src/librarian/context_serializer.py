"""
Context Serializer - Formats graph context for LLM consumption.
Converts raw graph data into compressed context blocks for Phase 2 integration.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom


@dataclass
class CompressedContextBlock:
    """Represents a compressed context block for LLM."""
    block_id: str
    block_type: str  # "file", "class", "function", "subgraph"
    content: str
    format: str  # "xml" or "markdown"
    token_count: int  # Estimated token count


class ContextSerializer:
    """
    Serializes graph context into LLM-friendly formats.
    Supports both XML and Markdown output for different context encoders.
    """
    
    def __init__(self, format: str = "xml"):
        """
        Initialize context serializer.
        
        Args:
            format: Output format ("xml" or "markdown")
        """
        self.format = format
        self.token_estimation_ratio = 4  # Average chars per token
    
    def serialize_file_context(
        self, 
        context: Dict[str, Any], 
        include_dependencies: bool = True
    ) -> CompressedContextBlock:
        """
        Serialize file context from retriever output.
        
        Args:
            context: File context dictionary from GraphRetriever.get_file_context()
            include_dependencies: Whether to include imported files
        
        Returns:
            CompressedContextBlock with serialized content
        """
        if self.format == "xml":
            content = self._serialize_file_to_xml(context, include_dependencies)
        else:
            content = self._serialize_file_to_markdown(context, include_dependencies)
        
        file_path = context.get("file", {}).get("path", "unknown")
        block_id = f"file_{Path(file_path).stem}"
        
        return CompressedContextBlock(
            block_id=block_id,
            block_type="file",
            content=content,
            format=self.format,
            token_count=len(content) // self.token_estimation_ratio
        )
    
    def serialize_subgraph(
        self, 
        files: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> CompressedContextBlock:
        """
        Serialize a multi-file subgraph.
        
        Args:
            files: List of file context dictionaries
            relationships: List of relationships between files
        
        Returns:
            CompressedContextBlock with serialized subgraph
        """
        if self.format == "xml":
            content = self._serialize_subgraph_to_xml(files, relationships)
        else:
            content = self._serialize_subgraph_to_markdown(files, relationships)
        
        return CompressedContextBlock(
            block_id=f"subgraph_{len(files)}_files",
            block_type="subgraph",
            content=content,
            format=self.format,
            token_count=len(content) // self.token_estimation_ratio
        )
    
    def serialize_symbol_definition(
        self, 
        symbol_name: str, 
        definitions: List[Dict[str, Any]]
    ) -> CompressedContextBlock:
        """
        Serialize symbol definition(s) with location context.
        
        Args:
            symbol_name: Name of the symbol
            definitions: List of definition records
        
        Returns:
            CompressedContextBlock with serialized definitions
        """
        if self.format == "xml":
            content = self._serialize_symbol_to_xml(symbol_name, definitions)
        else:
            content = self._serialize_symbol_to_markdown(symbol_name, definitions)
        
        return CompressedContextBlock(
            block_id=f"symbol_{symbol_name}",
            block_type="function",
            content=content,
            format=self.format,
            token_count=len(content) // self.token_estimation_ratio
        )
    
    # ===== XML Serialization =====
    
    def _serialize_file_to_xml(
        self, 
        context: Dict[str, Any], 
        include_dependencies: bool
    ) -> str:
        """Convert file context to XML format."""
        root = ET.Element("file")
        
        # File metadata
        file_info = context.get("file", {})
        ET.SubElement(root, "path").text = file_info.get("path", "")
        ET.SubElement(root, "language").text = file_info.get("language", "")
        ET.SubElement(root, "checksum").text = file_info.get("checksum", "")
        
        # Classes
        classes_elem = ET.SubElement(root, "classes")
        for class_def in context.get("classes", []):
            class_elem = ET.SubElement(classes_elem, "class")
            ET.SubElement(class_elem, "name").text = class_def.get("name", "")
            ET.SubElement(class_elem, "language").text = class_def.get("language", "")
        
        # Functions
        functions_elem = ET.SubElement(root, "functions")
        for func_def in context.get("functions", []):
            func_elem = ET.SubElement(functions_elem, "function")
            ET.SubElement(func_elem, "name").text = func_def.get("name", "")
            ET.SubElement(func_elem, "signature").text = func_def.get("signature", "")
            ET.SubElement(func_elem, "is_method").text = str(func_def.get("is_method", False))
        
        # Dependencies
        if include_dependencies:
            imports_elem = ET.SubElement(root, "imports")
            for imp in context.get("imports", []):
                import_elem = ET.SubElement(imports_elem, "import")
                ET.SubElement(import_elem, "target").text = imp.get("target", "")
        
        # Inheritance
        inheritance_elem = ET.SubElement(root, "inheritance")
        for inh in context.get("inheritance", []):
            inherit_elem = ET.SubElement(inheritance_elem, "inherits")
            ET.SubElement(inherit_elem, "parent").text = inh.get("parent", "")
            ET.SubElement(inherit_elem, "child").text = inh.get("child", "")
        
        return self._prettify_xml(root)
    
    def _serialize_subgraph_to_xml(
        self, 
        files: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> str:
        """Convert subgraph to XML format."""
        root = ET.Element("subgraph")
        
        # Files
        files_elem = ET.SubElement(root, "files")
        for file_ctx in files:
            file_elem = ET.SubElement(files_elem, "file")
            file_info = file_ctx.get("file", {})
            ET.SubElement(file_elem, "path").text = file_info.get("path", "")
            ET.SubElement(file_elem, "classes").text = str(len(file_ctx.get("classes", [])))
            ET.SubElement(file_elem, "functions").text = str(len(file_ctx.get("functions", [])))
        
        # Relationships
        rels_elem = ET.SubElement(root, "relationships")
        for rel in relationships:
            rel_elem = ET.SubElement(rels_elem, "relationship")
            ET.SubElement(rel_elem, "type").text = rel.get("type", "")
            ET.SubElement(rel_elem, "source").text = rel.get("source", "")
            ET.SubElement(rel_elem, "target").text = rel.get("target", "")
        
        return self._prettify_xml(root)
    
    def _serialize_symbol_to_xml(
        self, 
        symbol_name: str, 
        definitions: List[Dict[str, Any]]
    ) -> str:
        """Convert symbol definition to XML format."""
        root = ET.Element("symbol")
        ET.SubElement(root, "name").text = symbol_name
        
        defs_elem = ET.SubElement(root, "definitions")
        for defn in definitions:
            def_elem = ET.SubElement(defs_elem, "definition")
            ET.SubElement(def_elem, "type").text = defn.get("type", "")
            ET.SubElement(def_elem, "signature").text = defn.get("signature", "")
            ET.SubElement(def_elem, "file").text = Path(defn.get("file_path", "")).name
            ET.SubElement(def_elem, "language").text = defn.get("language", "")
        
        return self._prettify_xml(root)
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Pretty print XML with indentation."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    # ===== Markdown Serialization =====
    
    def _serialize_file_to_markdown(
        self, 
        context: Dict[str, Any], 
        include_dependencies: bool
    ) -> str:
        """Convert file context to Markdown format."""
        lines = []
        
        # File header
        file_info = context.get("file") or {}
        file_path = file_info.get("path", "unknown")
        lines.append(f"# File: {Path(file_path).name}")
        lines.append(f"**Language:** {file_info.get('language', 'unknown')}")
        checksum = file_info.get('checksum', '')
        lines.append(f"**Checksum:** {checksum[:8] if checksum else 'unknown'}...")
        lines.append("")
        
        # Classes
        if context.get("classes"):
            lines.append("## Classes")
            for class_def in context["classes"]:
                lines.append(f"- `{class_def['name']}` ({class_def.get('language', '')})")
            lines.append("")
        
        # Functions
        if context.get("functions"):
            lines.append("## Functions")
            for func_def in context["functions"]:
                is_method = " (method)" if func_def.get("is_method") else ""
                lines.append(f"- `{func_def['name']}{is_method}`")
                if func_def.get("signature"):
                    lines.append(f"  - Signature: `{func_def['signature']}`")
            lines.append("")
        
        # Dependencies
        if include_dependencies and context.get("imports"):
            lines.append("## Imports")
            for imp in context["imports"]:
                target_name = Path(imp["target"]).name if imp["target"] else "unknown"
                lines.append(f"- → `{target_name}`")
            lines.append("")
        
        # Inheritance
        if context.get("inheritance"):
            lines.append("## Inheritance")
            for inh in context["inheritance"]:
                lines.append(f"- `{inh['child']}` extends `{inh['parent']}`")
            lines.append("")
        
        return "\n".join(lines)
    
    def _serialize_subgraph_to_markdown(
        self, 
        files: List[Dict[str, Any]], 
        relationships: List[Dict[str, Any]]
    ) -> str:
        """Convert subgraph to Markdown format."""
        lines = []
        
        lines.append(f"# Subgraph: {len(files)} Files")
        lines.append("")
        
        # Files
        lines.append("## Files")
        for file_ctx in files:
            file_info = file_ctx.get("file", {})
            file_name = Path(file_info.get("path", "")).name
            class_count = len(file_ctx.get("classes", []))
            func_count = len(file_ctx.get("functions", []))
            lines.append(f"- `{file_name}` ({class_count} classes, {func_count} functions)")
        lines.append("")
        
        # Relationships
        if relationships:
            lines.append("## Relationships")
            for rel in relationships:
                source = Path(rel.get("source", "")).name
                target = Path(rel.get("target", "")).name
                rel_type = rel.get("type", "")
                lines.append(f"- `{source}` → `{target}` ({rel_type})")
            lines.append("")
        
        return "\n".join(lines)
    
    def _serialize_symbol_to_markdown(
        self, 
        symbol_name: str, 
        definitions: List[Dict[str, Any]]
    ) -> str:
        """Convert symbol definition to Markdown format."""
        lines = []
        
        lines.append(f"# Symbol: {symbol_name}")
        lines.append("")
        
        lines.append("## Definitions")
        for defn in definitions:
            file_name = Path(defn.get("file_path", "")).name
            lines.append(f"### {defn.get('type', 'Unknown')} in `{file_name}`")
            if defn.get("signature"):
                lines.append(f"```{defn.get('language', '')}") 
                lines.append(defn["signature"])
                lines.append("```")
            lines.append("")
        
        return "\n".join(lines)


def create_context_window(
    blocks: List[CompressedContextBlock], 
    max_tokens: int = 100000
) -> str:
    """
    Assemble multiple context blocks into a single context window.
    
    Args:
        blocks: List of compressed context blocks
        max_tokens: Maximum token limit for context window
    
    Returns:
        Combined context string that fits within token limit
    """
    total_tokens = 0
    combined_blocks = []
    
    for block in blocks:
        if total_tokens + block.token_count > max_tokens:
            break
        combined_blocks.append(block.content)
        total_tokens += block.token_count
    
    return "\n\n".join(combined_blocks)
