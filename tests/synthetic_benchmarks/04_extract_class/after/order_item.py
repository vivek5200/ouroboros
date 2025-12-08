"""Order item class."""

class OrderItem:
    """Extracted class for order items."""
    
    def __init__(self, name: str, price: float, quantity: int):
        self.name = name
        self.price = price
        self.quantity = quantity
    
    def get_subtotal(self) -> float:
        """Calculate item subtotal."""
        return self.price * self.quantity
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity
        }
