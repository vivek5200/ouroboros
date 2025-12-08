"""Math operations module."""

from calculator import add, subtract, multiply, divide

def calculate_total(prices: list[float]) -> float:
    """Calculate total sum of prices."""
    total = 0.0
    for price in prices:
        total = add(total, price)
    return total

def calculate_average(numbers: list[float]) -> float:
    """Calculate average of numbers."""
    if not numbers:
        return 0.0
    total = sum(numbers)
    return divide(total, len(numbers))
