"""
Test Project - User Authentication Module
"""

from typing import Optional
from datetime import datetime


class User:
    """Represents a user in the system."""
    
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email
        self.created_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class AuthService:
    """Authentication service."""
    
    def __init__(self):
        self.users = {}
    
    def register(self, username: str, email: str) -> User:
        """Register a new user."""
        user = User(username, email)
        self.users[username] = user
        return user
    
    def login(self, username: str, password: str) -> Optional[User]:
        """Authenticate user."""
        return self.users.get(username)


def create_auth_service() -> AuthService:
    """Factory function to create auth service."""
    return AuthService()
