"""Report generator."""

class ReportGenerator:
    def __init__(self, report_title: str):  # Changed from 'title'
        self.title = report_title
        self.data = []
    
    def add_data(self, data_item):  # Changed from 'item'
        """Add data to report."""
        self.data.append(data_item)
    
    def generate(self, output_format: str) -> str:  # Changed from 'format'
        """Generate report in specified format."""
        if output_format == "text":
            return self._generate_text()
        elif output_format == "html":
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
