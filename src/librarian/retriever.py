"""Retrieval API for GraphRAG queries."""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path.cwd()))

from src.librarian.graph_db import OuroborosGraphDB


@dataclass
class SubgraphNode:
    """Represents a node in the subgraph."""
    node_type: str  # File, Class, Function
    name: str
    path: Optional[str] = None
    signature: Optional[str] = None
    language: Optional[str] = None


@dataclass
class SubgraphEdge:
    """Represents an edge in the subgraph."""
    edge_type: str  # CONTAINS, IMPORTS, INHERITS_FROM, CALLS
    source: str
    target: str


class GraphRetriever:
    """Retrieval API for querying the code knowledge graph."""
    
    def __init__(self, db: OuroborosGraphDB):
        self.db = db
    
    def get_file_context(self, file_path: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Retrieve full context for a file with its dependencies.
        
        Args:
            file_path: Absolute path to the file
            max_depth: Maximum depth for dependency traversal (default: 2)
        
        Returns:
            Dictionary containing nodes, edges, and metadata
        """
        with self.db.driver.session() as session:
            # Get file node and all connected entities
            result = session.run("""
                MATCH (f:File {path: $path})
                OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
                OPTIONAL MATCH (c)-[:CONTAINS]->(m:Function)
                OPTIONAL MATCH (f)-[:CONTAINS]->(func:Function)
                OPTIONAL MATCH (f)-[imp:IMPORTS]->(imported:File)
                OPTIONAL MATCH (c)-[inh:INHERITS_FROM]->(parent:Class)
                RETURN 
                    f,
                    collect(DISTINCT {
                        type: 'Class',
                        name: c.name,
                        language: c.language
                    }) as classes,
                    collect(DISTINCT {
                        type: 'Function',
                        name: CASE WHEN m IS NOT NULL THEN m.name ELSE func.name END,
                        signature: CASE WHEN m IS NOT NULL THEN m.signature ELSE func.signature END,
                        is_method: m IS NOT NULL
                    }) as functions,
                    collect(DISTINCT {
                        type: 'IMPORTS',
                        target: imported.path
                    }) as imports,
                    collect(DISTINCT {
                        type: 'INHERITS_FROM',
                        parent: parent.name,
                        child: c.name
                    }) as inheritance
            """, path=file_path)
            
            record = result.single()
            if not record:
                return {"error": "File not found"}
            
            file_node = record["f"]
            
            return {
                "file": {
                    "path": file_node["path"],
                    "language": file_node.get("language"),
                    "checksum": file_node.get("checksum"),
                },
                "classes": [c for c in record["classes"] if c["name"] is not None],
                "functions": [f for f in record["functions"] if f["name"] is not None],
                "imports": [i for i in record["imports"] if i["target"] is not None],
                "inheritance": [h for h in record["inheritance"] if h["parent"] is not None],
            }
    
    def find_symbol_definition(self, symbol_name: str) -> List[Dict[str, Any]]:
        """
        Find where a class or function is defined.
        
        Args:
            symbol_name: Name of class or function to find
        
        Returns:
            List of definition locations with file paths
        """
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (f:File)-[:CONTAINS]->(entity)
                WHERE (entity:Class OR entity:Function) 
                  AND entity.name = $name
                RETURN 
                    labels(entity)[0] as type,
                    entity.name as name,
                    entity.signature as signature,
                    f.path as file_path,
                    f.language as language
            """, name=symbol_name)
            
            return [dict(record) for record in result]
    
    def find_symbol_usages(self, symbol_name: str) -> List[Dict[str, Any]]:
        """
        Find all usages of a symbol (imports, calls, inheritance).
        
        Args:
            symbol_name: Name of symbol to find usages
        
        Returns:
            List of usage locations
        """
        with self.db.driver.session() as session:
            # Find files that import the symbol's file
            result = session.run("""
                MATCH (source:File)-[:IMPORTS]->(target:File)
                MATCH (target)-[:CONTAINS]->(entity)
                WHERE (entity:Class OR entity:Function) 
                  AND entity.name = $name
                RETURN DISTINCT
                    'import' as usage_type,
                    source.path as source_file,
                    target.path as target_file,
                    entity.name as symbol_name
            """, name=symbol_name)
            
            usages = [dict(record) for record in result]
            
            # Find classes that inherit from it
            result = session.run("""
                MATCH (child:Class)-[:INHERITS_FROM]->(parent:Class {name: $name})
                MATCH (f:File)-[:CONTAINS]->(child)
                RETURN 
                    'inheritance' as usage_type,
                    f.path as source_file,
                    child.name as child_class,
                    parent.name as parent_class
            """, name=symbol_name)
            
            usages.extend([dict(record) for record in result])
            
            # Find functions that call it
            result = session.run("""
                MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $name})
                OPTIONAL MATCH (f:File)-[:CONTAINS]->(caller)
                OPTIONAL MATCH (c:Class)-[:CONTAINS]->(caller)
                RETURN 
                    'call' as usage_type,
                    f.path as source_file,
                    caller.name as caller_name,
                    callee.name as callee_name
            """, name=symbol_name)
            
            usages.extend([dict(record) for record in result])
            
            return usages
    
    def get_dependency_graph(self, file_path: str) -> Dict[str, Any]:
        """
        Get all files that depend on this file (transitive imports).
        
        Args:
            file_path: Absolute path to the file
        
        Returns:
            Dictionary with direct and transitive dependents
        """
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH path = (source:File)-[:IMPORTS*1..3]->(target:File {path: $path})
                RETURN 
                    source.path as dependent,
                    length(path) as distance,
                    [node in nodes(path) | node.path] as path_files
                ORDER BY distance
            """, path=file_path)
            
            dependents = []
            for record in result:
                dependents.append({
                    "file": record["dependent"],
                    "distance": record["distance"],
                    "path": record["path_files"],
                })
            
            return {
                "target": file_path,
                "dependent_count": len(dependents),
                "dependents": dependents,
            }
    
    def get_class_hierarchy(self, class_name: str) -> Dict[str, Any]:
        """
        Get inheritance hierarchy for a class.
        
        Args:
            class_name: Name of the class
        
        Returns:
            Dictionary with parents and children
        """
        with self.db.driver.session() as session:
            # Find parents (superclasses)
            result = session.run("""
                MATCH path = (child:Class {name: $name})-[:INHERITS_FROM*1..5]->(parent:Class)
                RETURN 
                    [node in nodes(path) | node.name] as hierarchy,
                    length(path) as depth
                ORDER BY depth DESC
                LIMIT 1
            """, name=class_name)
            
            parent_chain = []
            record = result.single()
            if record:
                parent_chain = record["hierarchy"]
            
            # Find children (subclasses)
            result = session.run("""
                MATCH (child:Class)-[:INHERITS_FROM]->(parent:Class {name: $name})
                RETURN child.name as child_name
            """, name=class_name)
            
            children = [r["child_name"] for r in result]
            
            return {
                "class": class_name,
                "parents": parent_chain[1:] if len(parent_chain) > 1 else [],
                "children": children,
            }
    
    def search_by_signature(self, signature_pattern: str) -> List[Dict[str, Any]]:
        """
        Search for functions by signature pattern.
        
        Args:
            signature_pattern: Regex pattern to match signatures
        
        Returns:
            List of matching functions with file locations
        """
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (f:File)-[:CONTAINS*1..2]->(func:Function)
                WHERE func.signature CONTAINS $pattern
                RETURN 
                    func.name as function_name,
                    func.signature as signature,
                    f.path as file_path,
                    func.start_line as line
            """, pattern=signature_pattern)
            
            return [dict(record) for record in result]
    
    def get_all_files_summary(self) -> List[Dict[str, Any]]:
        """Get summary statistics for all files in the graph."""
        with self.db.driver.session() as session:
            result = session.run("""
                MATCH (f:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
                OPTIONAL MATCH (f)-[:CONTAINS]->(func:Function)
                OPTIONAL MATCH (f)-[:IMPORTS]->(imported:File)
                RETURN 
                    f.path as path,
                    f.language as language,
                    count(DISTINCT c) as class_count,
                    count(DISTINCT func) as function_count,
                    count(DISTINCT imported) as import_count
                ORDER BY f.path
            """)
            
            return [dict(record) for record in result]
    
    def get_nodes_by_property(self, property_name: str, property_value: Any) -> List[Dict[str, Any]]:
        """
        Get nodes by a specific property value.
        
        Args:
            property_name: Name of the property to filter by
            property_value: Value to match
        
        Returns:
            List of matching nodes
        """
        with self.db.driver.session() as session:
            result = session.run(f"""
                MATCH (n)
                WHERE n.{property_name} = $value
                RETURN n
            """, value=property_value)
            
            return [dict(record["n"]) for record in result]
    
    def get_related_nodes(self, node_id: str, relationship_type: Optional[str] = None, max_depth: int = 1) -> List[Dict[str, Any]]:
        """
        Get nodes related to a given node.
        
        Args:
            node_id: ID or path of the starting node
            relationship_type: Optional relationship type to filter by
            max_depth: Maximum depth to traverse
        
        Returns:
            List of related nodes
        """
        with self.db.driver.session() as session:
            if relationship_type:
                result = session.run(f"""
                    MATCH (start)-[r:{relationship_type}*1..{max_depth}]-(related)
                    WHERE start.path = $node_id OR id(start) = $node_id
                    RETURN DISTINCT related
                """, node_id=node_id)
            else:
                result = session.run(f"""
                    MATCH (start)-[*1..{max_depth}]-(related)
                    WHERE start.path = $node_id OR id(start) = $node_id
                    RETURN DISTINCT related
                """, node_id=node_id)
            
            return [dict(record["related"]) for record in result]




def demo_retrieval_api():
    """Demonstrate the retrieval API capabilities."""
    from rich.console import Console
    from rich.json import JSON
    import json
    
    console = Console()
    
    console.print("\n[bold cyan]═══════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]       GraphRAG Retrieval API Demo[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════[/bold cyan]\n")
    
    db = OuroborosGraphDB()
    retriever = GraphRetriever(db)
    
    # 1. Get all files summary
    console.print("[bold yellow]1. Files Summary[/bold yellow]")
    files = retriever.get_all_files_summary()
    for f in files:
        console.print(f"  {Path(f['path']).name} ({f['language']}): "
                     f"{f['class_count']} classes, {f['function_count']} functions, "
                     f"{f['import_count']} imports")
    
    # 2. Get file context
    console.print("\n[bold yellow]2. File Context (userService.ts)[/bold yellow]")
    test_file = "g:/Just a Idea/tests/test_project/userService.ts"
    context = retriever.get_file_context(test_file)
    console.print(JSON(json.dumps(context, indent=2)))
    
    # 3. Find symbol definition
    console.print("\n[bold yellow]3. Find Symbol Definition (UserService)[/bold yellow]")
    definitions = retriever.find_symbol_definition("UserService")
    for d in definitions:
        console.print(f"  {d['type']}: {d['name']} in {Path(d['file_path']).name}")
    
    # 4. Find symbol usages
    console.print("\n[bold yellow]4. Find Symbol Usages (UserService)[/bold yellow]")
    usages = retriever.find_symbol_usages("UserService")
    if usages:
        for u in usages:
            console.print(f"  {u['usage_type']}: in {Path(u['source_file']).name}")
    else:
        console.print("  No usages found")
    
    # 5. Get dependency graph
    console.print("\n[bold yellow]5. Dependency Graph (types.ts)[/bold yellow]")
    test_file = "g:/Just a Idea/tests/test_project/types.ts"
    deps = retriever.get_dependency_graph(test_file)
    console.print(f"  Dependents: {deps['dependent_count']}")
    for dep in deps['dependents']:
        console.print(f"    {Path(dep['file']).name} (distance: {dep['distance']})")
    
    # 6. Search by signature
    console.print("\n[bold yellow]6. Search by Signature (async)[/bold yellow]")
    results = retriever.search_by_signature("async")
    for r in results:
        console.print(f"  {r['function_name']}: {r['signature']} "
                     f"in {Path(r['file_path']).name}:{r['line']}")
    
    console.print("\n[bold cyan]═══════════════════════════════════════════[/bold cyan]\n")
    
    db.close()


if __name__ == "__main__":
    demo_retrieval_api()
