"""Type definitions for user management."""

class UserProfile:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        self.address = None

class Address:
    def __init__(self, street: str, city: str, zip_code: str):
        self.street = street
        self.city = city
        self.zip_code = zip_code
