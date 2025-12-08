"""Data processing service."""

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self, item: str) -> str:
        """Process a data item."""
        return item.upper()
    
    def batch_process(self, items: list[str]) -> list[str]:
        """Process multiple items."""
        return [self.process(item) for item in items]
