"""Customer management system."""

class Customer:
    def __init__(self, customer_id: str, name: str):
        self.customer_id = customer_id
        self.name = name
        self.email_address = None  # Renamed from 'email'
        self.phone_number = None   # Renamed from 'phone'
    
    def update_contact(self, email_address: str, phone_number: str):
        """Update customer contact information."""
        previous_email = self.email_address
        previous_phone = self.phone_number
        self.email_address = email_address
        self.phone_number = phone_number
        return f"Updated from {previous_email}/{previous_phone} to {email_address}/{phone_number}"
