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
