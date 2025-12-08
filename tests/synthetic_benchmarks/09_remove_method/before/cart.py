"""Shopping cart."""

class ShoppingCart:
    def __init__(self):
        self.items = []
        self.discount_code = None
    
    def add_item(self, item):
        """Add item to cart."""
        self.items.append(item)
    
    def remove_item(self, item_id):
        """Remove item from cart."""
        self.items = [item for item in self.items if item['id'] != item_id]
    
    def get_total(self) -> float:
        """Calculate cart total."""
        return sum(item['price'] for item in self.items)
    
    def clear(self):
        """Clear all items from cart."""
        self.items = []
        self.discount_code = None
    
    def apply_discount_code(self, code: str):
        """Apply discount code to cart."""
        self.discount_code = code
