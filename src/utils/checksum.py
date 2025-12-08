"""
Ouroboros - File Checksum Utilities
Provides deterministic hashing for file content tracking.
"""

import hashlib
from pathlib import Path
from typing import Union


def calculate_file_checksum(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Calculate cryptographic hash of file content.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (sha256, sha512, md5)
        
    Returns:
        Hexadecimal hash string
        
    Example:
        >>> checksum = calculate_file_checksum("src/auth.ts")
        >>> print(checksum)
        'a3f5b9c2e1d4f6a8b7c9e0d1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1'
    """
    hasher = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def calculate_string_checksum(content: str, algorithm: str = "sha256") -> str:
    """
    Calculate cryptographic hash of string content.
    
    Args:
        content: String content to hash
        algorithm: Hash algorithm (sha256, sha512, md5)
        
    Returns:
        Hexadecimal hash string
        
    Example:
        >>> checksum = calculate_string_checksum("function hello() {}")
        >>> print(checksum)
        'b4d8c3f9a2e1d5f7a9c0b8e3d4f6a2b5c7e8d9f0a1b2c3d4e5f6a7b8c9d0e1f2'
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()


def verify_file_integrity(file_path: Union[str, Path], expected_checksum: str) -> bool:
    """
    Verify file content matches expected checksum.
    
    Args:
        file_path: Path to the file
        expected_checksum: Expected hash value
        
    Returns:
        True if checksums match, False otherwise
        
    Example:
        >>> is_valid = verify_file_integrity("src/auth.ts", stored_checksum)
        >>> if not is_valid:
        ...     print("File has been modified!")
    """
    actual_checksum = calculate_file_checksum(file_path)
    return actual_checksum == expected_checksum
