"""Benchmark 1: Rename Import - Change import statement."""

# AFTER: Import from 'user_types' (file renamed)
from user_types import UserProfile, Address

class UserManager:
    def __init__(self):
        self.users = []
    
    def create_user(self, name: str, email: str) -> UserProfile:
        profile = UserProfile(name, email)
        self.users.append(profile)
        return profile
    
    def update_address(self, user: UserProfile, address: Address) -> None:
        user.address = address
