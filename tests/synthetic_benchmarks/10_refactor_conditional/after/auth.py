"""User authentication."""

class Authenticator:
    def __init__(self):
        self.users = {}
    
    def validate_password(self, password: str) -> bool:
        """Validate password strength with simplified logic."""
        if len(password) < 8:
            return False
        
        has_upper = any(char.isupper() for char in password)
        has_lower = any(char.islower() for char in password)
        has_digit = any(char.isdigit() for char in password)
        
        return has_upper and has_lower and has_digit
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user with simplified logic."""
        return username in self.users and self.users[username] == password
