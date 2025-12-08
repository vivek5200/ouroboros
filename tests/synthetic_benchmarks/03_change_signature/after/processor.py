"""Data processing service."""

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self, item: str, uppercase: bool = True) -> str:
        """Process a data item with optional uppercase conversion."""
        if uppercase:
            return item.upper()
        return item.lower()
    
    def batch_process(self, items: list[str], uppercase: bool = True) -> list[str]:
        """Process multiple items with optional uppercase conversion."""
        return [self.process(item, uppercase) for item in items]
