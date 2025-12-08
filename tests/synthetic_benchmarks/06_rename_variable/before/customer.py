"""Customer management system."""

class Customer:
    def __init__(self, customer_id: str, name: str):
        self.customer_id = customer_id
        self.name = name
        self.email = None
        self.phone = None
    
    def update_contact(self, email: str, phone: str):
        """Update customer contact information."""
        old_email = self.email
        old_phone = self.phone
        self.email = email
        self.phone = phone
        return f"Updated from {old_email}/{old_phone} to {email}/{phone}"
