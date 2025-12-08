"""Product catalog."""

class Product:
    def __init__(self, product_id: str, name: str, price: float):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.inventory = 0
    
    def get_info(self) -> str:
        """Get product information."""
        return f"{self.name} (${self.price})"
    
    def update_inventory(self, quantity: int) -> None:
        """NEW METHOD: Update inventory quantity."""
        self.inventory += quantity
    
    def is_in_stock(self) -> bool:
        """NEW METHOD: Check if product is in stock."""
        return self.inventory > 0
    
    def apply_discount(self, percentage: float) -> float:
        """NEW METHOD: Calculate discounted price."""
        discount_amount = self.price * (percentage / 100)
        return self.price - discount_amount
