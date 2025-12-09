"""
Ouroboros - Graph Database Connection & Operations
Handles Neo4j connection with provenance-aware CRUD operations.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from neo4j import GraphDatabase as Neo4jDriver
from neo4j.exceptions import ServiceUnavailable, SessionExpired, AuthError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class OuroborosGraphDB:
    """
    Neo4j connection manager with provenance metadata tracking.
    
    Features:
    - Automatic connection retry with exponential backoff
    - Connection pooling with configurable pool size
    - Session timeout and max lifetime management
    - Comprehensive error handling for auth/network failures
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        max_connection_lifetime: int = 3600,  # 1 hour
        max_connection_pool_size: int = 50,
        connection_timeout: float = 30.0,
        max_retry_attempts: int = 3,
        retry_backoff_factor: float = 2.0
    ):
        """
        Initialize Neo4j connection with reliability features.
        
        Args:
            uri: Neo4j connection URI (defaults to env NEO4J_URI)
            user: Neo4j username (defaults to env NEO4J_USER)
            password: Neo4j password (defaults to env NEO4J_PASSWORD)
            model_name: Component name for provenance (defaults to env MODEL_NAME)
            model_version: Component version (defaults to env MODEL_VERSION)
            max_connection_lifetime: Max lifetime of pooled connections in seconds
            max_connection_pool_size: Max number of connections in pool
            connection_timeout: Timeout for establishing connections
            max_retry_attempts: Number of retry attempts for failed operations
            retry_backoff_factor: Exponential backoff multiplier
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "ouroboros123")
        self.model_name = model_name or os.getenv("MODEL_NAME", "ouroboros-librarian")
        self.model_version = model_version or os.getenv("MODEL_VERSION", "1.0.0")
        
        # Retry configuration
        self.max_retry_attempts = max_retry_attempts
        self.retry_backoff_factor = retry_backoff_factor
        
        # Create driver with connection pool configuration
        self.driver = Neo4jDriver.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_lifetime=max_connection_lifetime,
            max_connection_pool_size=max_connection_pool_size,
            connection_timeout=connection_timeout,
            connection_acquisition_timeout=connection_timeout
        )
        
        # Verify connection on initialization
        self._verify_connectivity()
    
    def _verify_connectivity(self) -> None:
        """
        Verify Neo4j connection is working with retry logic.
        
        Raises:
            AuthError: If authentication fails after retries
            ServiceUnavailable: If Neo4j is unreachable after retries
        """
        for attempt in range(self.max_retry_attempts):
            try:
                with self.driver.session() as session:
                    result = session.run("RETURN 1 AS num")
                    result.single()
                    logger.info(f"✓ Neo4j connection verified: {self.uri}")
                    return
            except AuthError as e:
                logger.error(f"✗ Neo4j authentication failed: {e}")
                raise  # Don't retry auth errors
            except ServiceUnavailable as e:
                if attempt < self.max_retry_attempts - 1:
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(
                        f"⚠ Neo4j unavailable (attempt {attempt + 1}/{self.max_retry_attempts}), "
                        f"retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"✗ Neo4j connection failed after {self.max_retry_attempts} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"✗ Unexpected error during connection verification: {e}")
                raise
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """
        Execute a database operation with automatic retry on transient failures.
        
        Args:
            operation: Function to execute
            *args, **kwargs: Arguments to pass to operation
        
        Returns:
            Result of the operation
        
        Raises:
            Exception: If operation fails after all retries
        """
        for attempt in range(self.max_retry_attempts):
            try:
                return operation(*args, **kwargs)
            except (ServiceUnavailable, SessionExpired) as e:
                if attempt < self.max_retry_attempts - 1:
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(
                        f"⚠ Database operation failed (attempt {attempt + 1}/{self.max_retry_attempts}), "
                        f"retrying in {wait_time:.1f}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                    # Recreate driver on connection failures
                    self.driver.close()
                    self.driver = Neo4jDriver.driver(
                        self.uri,
                        auth=(self.user, self.password)
                    )
                else:
                    logger.error(f"✗ Operation failed after {self.max_retry_attempts} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"✗ Unexpected error in database operation: {e}")
                raise
    
    def close(self):
        """Close the database connection."""
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _generate_provenance(self, prompt_id: Optional[str] = None) -> Dict[str, str]:
        """
        Generate provenance metadata for a node/edge.
        
        Args:
            prompt_id: Unique identifier for the operation (auto-generated if None)
            
        Returns:
            Dictionary with provenance fields
        """
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "prompt_id": prompt_id or f"prompt_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def create_file_node(
        self,
        path: str,
        language: str,
        content: str,
        context_checksum: str,
        metadata: Optional[Dict[str, Any]] = None,
        prompt_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a :File node with provenance metadata.
        
        Args:
            path: Absolute file path
            language: Programming language (typescript, python, etc.)
            content: Raw file content
            context_checksum: SHA256 hash of content
            metadata: Additional metadata fields
            prompt_id: Operation identifier
            
        Returns:
            Created node properties
        """
        provenance = self._generate_provenance(prompt_id)
        metadata = metadata or {}
        
        query = """
        MERGE (f:File {path: $path})
        SET f.language = $language,
            f.content = $content,
            f.context_checksum = $context_checksum,
            f.model_name = $model_name,
            f.model_version = $model_version,
            f.prompt_id = $prompt_id,
            f.timestamp = $timestamp,
            f.line_count = $line_count,
            f.size_bytes = $size_bytes
        RETURN f
        """
        
        def _create():
            with self.driver.session() as session:
                result = session.run(
                    query,
                    path=path,
                    language=language,
                    content=content,
                    context_checksum=context_checksum,
                    line_count=len(content.split("\n")),
                    size_bytes=len(content.encode("utf-8")),
                    **provenance,
                    **metadata
                )
                return dict(result.single()["f"])
        
        return self._execute_with_retry(_create)
    
    def create_class_node(
        self,
        name: str,
        fully_qualified_name: str,
        file_path: str,
        start_line: int,
        end_line: int,
        is_exported: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        prompt_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a :Class node linked to its parent :File.
        
        Args:
            name: Class name
            fully_qualified_name: Full namespace path (e.g., "module.ClassName")
            file_path: Parent file path
            start_line: Starting line number
            end_line: Ending line number
            is_exported: Whether the class is exported
            metadata: Additional metadata
            prompt_id: Operation identifier
            
        Returns:
            Created node properties
        """
        provenance = self._generate_provenance(prompt_id)
        metadata = metadata or {}
        
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (c:Class {fully_qualified_name: $fqn})
        SET c.name = $name,
            c.start_line = $start_line,
            c.end_line = $end_line,
            c.is_exported = $is_exported,
            c.model_name = $model_name,
            c.model_version = $model_version,
            c.prompt_id = $prompt_id,
            c.timestamp = $timestamp
        MERGE (f)-[:CONTAINS]->(c)
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                name=name,
                fqn=fully_qualified_name,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                is_exported=is_exported,
                **provenance,
                **metadata
            )
            return dict(result.single()["c"])
    
    def create_function_node(
        self,
        name: str,
        signature: str,
        file_path: str,
        start_line: int,
        end_line: int,
        parent_class: Optional[str] = None,
        is_async: bool = False,
        is_exported: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        prompt_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a :Function node.
        
        Args:
            name: Function name
            signature: Full function signature
            file_path: Parent file path
            start_line: Starting line number
            end_line: Ending line number
            parent_class: Parent class FQN if this is a method
            is_async: Whether the function is async
            is_exported: Whether the function is exported
            metadata: Additional metadata
            prompt_id: Operation identifier
            
        Returns:
            Created node properties
        """
        provenance = self._generate_provenance(prompt_id)
        metadata = metadata or {}
        
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (fn:Function {signature: $signature})
        SET fn.name = $name,
            fn.start_line = $start_line,
            fn.end_line = $end_line,
            fn.is_async = $is_async,
            fn.is_exported = $is_exported,
            fn.model_name = $model_name,
            fn.model_version = $model_version,
            fn.prompt_id = $prompt_id,
            fn.timestamp = $timestamp
        MERGE (f)-[:CONTAINS]->(fn)
        """
        
        # If parent class exists, link to it
        if parent_class:
            query += """
            WITH fn
            MATCH (c:Class {fully_qualified_name: $parent_class})
            MERGE (c)-[:CONTAINS]->(fn)
            """
        
        query += " RETURN fn"
        
        with self.driver.session() as session:
            result = session.run(
                query,
                name=name,
                signature=signature,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                is_async=is_async,
                is_exported=is_exported,
                parent_class=parent_class,
                **provenance,
                **metadata
            )
            return dict(result.single()["fn"])
    
    def create_import_edge(
        self,
        from_file: str,
        to_file: str,
        import_names: List[str],
        prompt_id: Optional[str] = None
    ):
        """
        Create an :IMPORTS relationship between files.
        
        Args:
            from_file: Source file path
            to_file: Target file path
            import_names: List of imported symbols
            prompt_id: Operation identifier
        """
        provenance = self._generate_provenance(prompt_id)
        
        query = """
        MATCH (f1:File {path: $from_file})
        MATCH (f2:File {path: $to_file})
        MERGE (f1)-[r:IMPORTS]->(f2)
        SET r.symbols = $import_names,
            r.model_name = $model_name,
            r.model_version = $model_version,
            r.prompt_id = $prompt_id,
            r.timestamp = $timestamp
        RETURN r
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                from_file=from_file,
                to_file=to_file,
                import_names=import_names,
                **provenance
            )
    
    def create_inherits_edge(
        self,
        child_class: str,
        parent_class: str,
        prompt_id: Optional[str] = None
    ):
        """
        Create an :INHERITS_FROM relationship between classes.
        
        Args:
            child_class: Child class FQN
            parent_class: Parent class FQN
            prompt_id: Operation identifier
        """
        provenance = self._generate_provenance(prompt_id)
        
        query = """
        MATCH (c1:Class {fully_qualified_name: $child_class})
        MATCH (c2:Class {fully_qualified_name: $parent_class})
        MERGE (c1)-[r:INHERITS_FROM]->(c2)
        SET r.model_name = $model_name,
            r.model_version = $model_version,
            r.prompt_id = $prompt_id,
            r.timestamp = $timestamp
        RETURN r
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                child_class=child_class,
                parent_class=parent_class,
                **provenance
            )
    
    def create_calls_edge(
        self,
        caller_signature: str,
        callee_signature: str,
        call_count: int = 1,
        prompt_id: Optional[str] = None
    ):
        """
        Create a :CALLS relationship between functions.
        
        Args:
            caller_signature: Calling function signature
            callee_signature: Called function signature
            call_count: Number of times the function is called
            prompt_id: Operation identifier
        """
        provenance = self._generate_provenance(prompt_id)
        
        query = """
        MATCH (fn1:Function {signature: $caller})
        MATCH (fn2:Function {signature: $callee})
        MERGE (fn1)-[r:CALLS]->(fn2)
        SET r.call_count = $call_count,
            r.model_name = $model_name,
            r.model_version = $model_version,
            r.prompt_id = $prompt_id,
            r.timestamp = $timestamp
        RETURN r
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                caller=caller_signature,
                callee=callee_signature,
                call_count=call_count,
                **provenance
            )
    
    def get_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file node by path.
        
        Args:
            path: File path
            
        Returns:
            Node properties or None if not found
        """
        query = "MATCH (f:File {path: $path}) RETURN f"
        
        with self.driver.session() as session:
            result = session.run(query, path=path)
            record = result.single()
            return dict(record["f"]) if record else None
    
    def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute raw Cypher query with retry logic.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records
        """
        def _execute():
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        
        return self._execute_with_retry(_execute)
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Execute query and return raw records (alias for backward compatibility).
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records
        """
        def _execute():
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return list(result)
        
        return self._execute_with_retry(_execute)
