"""User authentication."""

class Authenticator:
    def __init__(self):
        self.users = {}
    
    def validate_password(self, password: str) -> bool:
        """Validate password strength."""
        if len(password) < 8:
            return False
        
        has_upper = False
        has_lower = False
        has_digit = False
        
        for char in password:
            if char.isupper():
                has_upper = True
            if char.islower():
                has_lower = True
            if char.isdigit():
                has_digit = True
        
        if has_upper and has_lower and has_digit:
            return True
        else:
            return False
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user."""
        if username in self.users:
            if self.users[username] == password:
                return True
            else:
                return False
        else:
            return False
