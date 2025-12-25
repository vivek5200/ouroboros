"""
Dependency impact analysis using graph traversal.

Analyzes the Neo4j graph to identify files affected by refactoring operations.
Queries CALLS, IMPORTS, and INHERITS_FROM edges to build comprehensive
dependency information for RefactorPlan generation.
"""

import logging
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass

from src.librarian.graph_db import OuroborosGraphDB
from src.librarian.retriever import GraphRetriever


logger = logging.getLogger(__name__)


@dataclass
class DependencyNode:
    """Represents a code element and its dependencies."""
    
    file_path: str
    symbol_name: str
    symbol_type: str  # 'function', 'class', 'method'
    
    # Dependencies
    calls_to: List[str] = None  # Functions this symbol calls
    called_by: List[str] = None  # Functions that call this symbol
    imports_from: List[str] = None  # Files this file imports
    imported_by: List[str] = None  # Files that import this file
    inherits_from: List[str] = None  # Parent classes
    inherited_by: List[str] = None  # Child classes
    
    def __post_init__(self):
        """Initialize lists if None."""
        self.calls_to = self.calls_to or []
        self.called_by = self.called_by or []
        self.imports_from = self.imports_from or []
        self.imported_by = self.imported_by or []
        self.inherits_from = self.inherits_from or []
        self.inherited_by = self.inherited_by or []


class DependencyAnalyzer:
    """
    Analyzes code dependencies using graph traversal.
    
    Provides impact analysis for refactoring operations by traversing
    the Neo4j graph to find all code elements affected by a change.
    """
    
    def __init__(self, db: Optional[OuroborosGraphDB] = None):
        """
        Initialize analyzer.
        
        Args:
            db: Neo4j database connection (creates new if None)
        """
        self.db = db or OuroborosGraphDB()
        self.retriever = GraphRetriever(self.db)
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """
        Get dependencies for a node.
        
        Args:
            node_id: Node identifier
        
        Returns:
            List of dependency identifiers
        """
        return []  # Simple stub for now

    
    def analyze_function_rename(
        self,
        file_path: str,
        function_name: str
    ) -> Dict[str, Any]:
        """
        Analyze impact of renaming a function.
        
        Args:
            file_path: File containing the function
            function_name: Name of function to rename
        
        Returns:
            Dictionary with affected files and impact types
        """
        
        logger.info(f"Analyzing rename impact for {function_name} in {file_path}")
        
        # Query: Find all call sites
        query = """
        MATCH (file:File {path: $file_path})-[:CONTAINS]->(func:Function {name: $func_name})
        OPTIONAL MATCH (caller:Function)-[call:CALLS]->(func)
        OPTIONAL MATCH (caller)<-[:CONTAINS]-(caller_file:File)
        RETURN 
            caller.name as caller_name,
            caller_file.path as caller_file,
            collect(DISTINCT caller_file.path) as affected_files
        """
        
        result = self.db.execute_query(query, {
            "file_path": file_path,
            "func_name": function_name
        })
        
        affected_files = set()
        call_sites = []
        
        for record in result:
            if record["caller_file"]:
                affected_files.add(record["caller_file"])
                call_sites.append({
                    "file": record["caller_file"],
                    "caller": record["caller_name"],
                    "impact_type": "call"
                })
        
        # Check imports (functions exported from this file)
        import_query = """
        MATCH (source:File {path: $file_path})
        MATCH (importer:File)-[imp:IMPORTS]->(source)
        RETURN importer.path as importer_path
        """
        
        import_result = self.db.execute_query(import_query, {"file_path": file_path})
        
        for record in import_result:
            affected_files.add(record["importer_path"])
            call_sites.append({
                "file": record["importer_path"],
                "impact_type": "import"
            })
        
        return {
            "affected_files": list(affected_files),
            "call_sites": call_sites,
            "estimated_impact": len(affected_files),
            "risk_level": self._assess_risk_level(len(affected_files), len(call_sites))
        }
    
    def analyze_class_rename(
        self,
        file_path: str,
        class_name: str
    ) -> Dict[str, Any]:
        """
        Analyze impact of renaming a class.
        
        Args:
            file_path: File containing the class
            class_name: Name of class to rename
        
        Returns:
            Dictionary with affected files and impact types
        """
        
        logger.info(f"Analyzing class rename impact for {class_name} in {file_path}")
        
        affected_files = set()
        impacts = []
        
        # Find classes that inherit from this class
        inheritance_query = """
        MATCH (parent:Class {name: $class_name})<-[:INHERITS_FROM]-(child:Class)
        MATCH (child)<-[:CONTAINS]-(child_file:File)
        RETURN child.name as child_name, child_file.path as child_file
        """
        
        result = self.db.execute_query(inheritance_query, {"class_name": class_name})
        
        for record in result:
            affected_files.add(record["child_file"])
            impacts.append({
                "file": record["child_file"],
                "child_class": record["child_name"],
                "impact_type": "inheritance"
            })
        
        # Find files that import this class
        import_query = """
        MATCH (source:File {path: $file_path})
        MATCH (importer:File)-[imp:IMPORTS]->(source)
        RETURN importer.path as importer_path
        """
        
        import_result = self.db.execute_query(import_query, {"file_path": file_path})
        
        for record in import_result:
            affected_files.add(record["importer_path"])
            impacts.append({
                "file": record["importer_path"],
                "impact_type": "import"
            })
        
        return {
            "affected_files": list(affected_files),
            "impacts": impacts,
            "estimated_impact": len(affected_files),
            "risk_level": self._assess_risk_level(len(affected_files), len(impacts))
        }
    
    def get_symbol_dependencies(
        self,
        file_path: str,
        symbol_name: str,
        symbol_type: str = "function"
    ) -> DependencyNode:
        """
        Get comprehensive dependency information for a symbol.
        
        Args:
            file_path: File containing the symbol
            symbol_name: Name of the symbol
            symbol_type: Type of symbol ('function', 'class', 'method')
        
        Returns:
            DependencyNode with all dependencies
        """
        
        node = DependencyNode(
            file_path=file_path,
            symbol_name=symbol_name,
            symbol_type=symbol_type
        )
        
        if symbol_type in ["function", "method"]:
            # Get function calls
            calls_query = """
            MATCH (file:File {path: $file_path})-[:CONTAINS]->(func:Function {name: $symbol_name})
            OPTIONAL MATCH (func)-[:CALLS]->(callee:Function)
            OPTIONAL MATCH (caller:Function)-[:CALLS]->(func)
            RETURN 
                collect(DISTINCT callee.name) as calls_to,
                collect(DISTINCT caller.name) as called_by
            """
            
            result = self.db.execute_query(calls_query, {
                "file_path": file_path,
                "symbol_name": symbol_name
            })
            
            if result:
                record = result[0]
                node.calls_to = [c for c in record["calls_to"] if c]
                node.called_by = [c for c in record["called_by"] if c]
        
        elif symbol_type == "class":
            # Get inheritance relationships (full chain)
            inheritance_query = """
            MATCH (file:File {path: $file_path})-[:CONTAINS]->(cls:Class {name: $symbol_name})
            OPTIONAL MATCH path = (cls)-[:INHERITS_FROM*1..5]->(ancestor:Class)
            OPTIONAL MATCH (descendant:Class)-[:INHERITS_FROM*1..5]->(cls)
            RETURN 
                collect(DISTINCT ancestor.name) as inherits_from,
                collect(DISTINCT descendant.name) as inherited_by,
                [node in nodes(path) | node.name] as inheritance_chain
            """
            
            result = self.db.execute_query(inheritance_query, {
                "file_path": file_path,
                "symbol_name": symbol_name
            })
            
            if result:
                record = result[0]
                node.inherits_from = [c for c in record["inherits_from"] if c]
                node.inherited_by = [c for c in record["inherited_by"] if c]
        
        # Get file-level imports
        import_query = """
        MATCH (file:File {path: $file_path})
        OPTIONAL MATCH (file)-[:IMPORTS]->(imported:File)
        OPTIONAL MATCH (importer:File)-[:IMPORTS]->(file)
        RETURN 
            collect(DISTINCT imported.path) as imports_from,
            collect(DISTINCT importer.path) as imported_by
        """
        
        result = self.db.execute_query(import_query, {"file_path": file_path})
        
        if result:
            record = result[0]
            node.imports_from = [f for f in record["imports_from"] if f]
            node.imported_by = [f for f in record["imported_by"] if f]
        
        return node
    
    def resolve_symbol_scope(
        self,
        symbol_name: str,
        context_file: str,
        symbol_type: str = "function"
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve a symbol's definition using scope rules.
        
        Searches in order:
        1. Same file
        2. Direct imports
        3. Transitive imports (depth 2)
        
        Args:
            symbol_name: Symbol to resolve
            context_file: File where symbol is referenced
            symbol_type: Type of symbol ('function', 'class')
        
        Returns:
            Dictionary with definition location or None if not found
        """
        logger.info(f"Resolving scope for {symbol_name} from {context_file}")
        
        # Search order: same file -> direct imports -> transitive imports
        scope_query = """
        MATCH (context:File {path: $context_file})
        OPTIONAL MATCH (context)-[:CONTAINS]->(local)
        WHERE (local:Class OR local:Function) AND local.name = $symbol_name
        
        OPTIONAL MATCH (context)-[:IMPORTS]->(direct:File)-[:CONTAINS]->(direct_symbol)
        WHERE (direct_symbol:Class OR direct_symbol:Function) AND direct_symbol.name = $symbol_name
        
        OPTIONAL MATCH (context)-[:IMPORTS*2]->(transitive:File)-[:CONTAINS]->(trans_symbol)
        WHERE (trans_symbol:Class OR trans_symbol:Function) AND trans_symbol.name = $symbol_name
        
        RETURN 
            local.name as local_match,
            CASE WHEN local IS NOT NULL THEN context.path ELSE NULL END as local_file,
            direct_symbol.name as direct_match,
            direct.path as direct_file,
            trans_symbol.name as transitive_match,
            transitive.path as transitive_file
        LIMIT 1
        """
        
        result = self.db.execute_query(scope_query, {
            "context_file": context_file,
            "symbol_name": symbol_name
        })
        
        if not result:
            return None
        
        record = result[0]
        
        # Return first match by scope priority
        if record.get("local_match"):
            return {
                "symbol": symbol_name,
                "file": record["local_file"],
                "scope": "local",
                "distance": 0
            }
        elif record.get("direct_match"):
            return {
                "symbol": symbol_name,
                "file": record["direct_file"],
                "scope": "direct_import",
                "distance": 1
            }
        elif record.get("transitive_match"):
            return {
                "symbol": symbol_name,
                "file": record["transitive_file"],
                "scope": "transitive_import",
                "distance": 2
            }
        
        return None
    
    def get_inheritance_chain(
        self,
        class_name: str,
        direction: str = "ancestors"
    ) -> List[Dict[str, Any]]:
        """
        Get full inheritance chain for a class.
        
        Args:
            class_name: Starting class name
            direction: 'ancestors' for parents, 'descendants' for children
        
        Returns:
            List of classes in inheritance chain with metadata
        """
        if direction == "ancestors":
            query = """
            MATCH path = (child:Class {name: $class_name})-[:INHERITS_FROM*1..10]->(ancestor:Class)
            MATCH (ancestor)<-[:CONTAINS]-(f:File)
            RETURN 
                ancestor.name as class_name,
                f.path as file_path,
                length(path) as distance,
                [node in nodes(path) | node.name] as chain
            ORDER BY distance
            """
        else:  # descendants
            query = """
            MATCH path = (descendant:Class)-[:INHERITS_FROM*1..10]->(parent:Class {name: $class_name})
            MATCH (descendant)<-[:CONTAINS]-(f:File)
            RETURN 
                descendant.name as class_name,
                f.path as file_path,
                length(path) as distance,
                [node in nodes(path) | node.name] as chain
            ORDER BY distance
            """
        
        result = self.db.execute_query(query, {"class_name": class_name})
        
        return [
            {
                "class": record["class_name"],
                "file": record["file_path"],
                "distance": record["distance"],
                "chain": record["chain"]
            }
            for record in result
        ]
    
    def find_transitive_dependencies(
        self,
        file_path: str,
        max_depth: int = 3
    ) -> Set[str]:
        """
        Find all files transitively dependent on the given file.
        
        Args:
            file_path: Starting file
            max_depth: Maximum traversal depth
        
        Returns:
            Set of file paths
        """
        
        query = """
        MATCH path = (start:File {path: $file_path})<-[:IMPORTS*1..""" + str(max_depth) + """]->(dependent:File)
        RETURN DISTINCT dependent.path as dep_path
        """
        
        result = self.db.execute_query(query, {"file_path": file_path})
        
        return {record["dep_path"] for record in result}
    
    def _assess_risk_level(self, num_files: int, num_impacts: int) -> str:
        """
        Assess risk level based on impact scope.
        
        Args:
            num_files: Number of affected files
            num_impacts: Number of individual impacts
        
        Returns:
            Risk level string: low, medium, high, critical
        """
        
        if num_files == 0 and num_impacts == 0:
            return "low"
        elif num_files <= 2 and num_impacts <= 5:
            return "low"
        elif num_files <= 5 and num_impacts <= 15:
            return "medium"
        elif num_files <= 10 and num_impacts <= 30:
            return "high"
        else:
            return "critical"
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
