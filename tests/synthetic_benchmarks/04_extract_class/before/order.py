"""Order management system."""

class Order:
    def __init__(self, order_id: str):
        self.order_id = order_id
        self.items = []
        self.total = 0.0
    
    def add_item(self, name: str, price: float, quantity: int):
        """Add item to order."""
        self.items.append({
            'name': name,
            'price': price,
            'quantity': quantity
        })
        self.total += price * quantity
    
    def remove_item(self, name: str):
        """Remove item from order."""
        self.items = [item for item in self.items if item['name'] != name]
        self._recalculate_total()
    
    def _recalculate_total(self):
        """Recalculate order total."""
        self.total = sum(item['price'] * item['quantity'] for item in self.items)
    
    def apply_discount(self, percentage: float):
        """Apply percentage discount."""
        self.total = self.total * (1 - percentage / 100)
    
    def get_summary(self) -> str:
        """Get order summary."""
        return f"Order {self.order_id}: {len(self.items)} items, Total: ${self.total:.2f}"
