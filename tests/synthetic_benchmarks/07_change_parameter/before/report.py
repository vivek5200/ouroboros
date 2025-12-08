"""Report generator."""

class ReportGenerator:
    def __init__(self, title: str):
        self.title = title
        self.data = []
    
    def add_data(self, item):
        """Add data to report."""
        self.data.append(item)
    
    def generate(self, format: str) -> str:
        """Generate report in specified format."""
        if format == "text":
            return self._generate_text()
        elif format == "html":
            return self._generate_html()
        return "Unsupported format"
    
    def _generate_text(self) -> str:
        """Generate text report."""
        lines = [self.title, "=" * len(self.title)]
        for item in self.data:
            lines.append(f"- {item}")
        return "\n".join(lines)
    
    def _generate_html(self) -> str:
        """Generate HTML report."""
        html = f"<h1>{self.title}</h1><ul>"
        for item in self.data:
            html += f"<li>{item}</li>"
        html += "</ul>"
        return html
