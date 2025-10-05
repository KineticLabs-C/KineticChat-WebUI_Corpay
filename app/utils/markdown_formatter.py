"""
Markdown Formatter Utility
Formats text with proper markdown for links, phone numbers, and other elements
"""

import re
from typing import Dict, Any

class MarkdownFormatter:
    """Formats response text with proper markdown"""
    
    def __init__(self):
        # Phone number patterns
        self.phone_patterns = [
            (r'\b1-844-708-1821\b', '[1-844-708-1821](tel:18447081821)'),
        ]
        
        # URL patterns that need markdown formatting
        self.url_patterns = [
            # YourPharmacy Health main site
            (r'visit YourPharmacy Health\'s ([\w\s]+) page', r'visit [YourPharmacy Health\'s \1 page](https://yourpharmacy.example.com)'),
            (r'YourPharmacy Health website', '[YourPharmacy Health website](https://yourpharmacy.example.com)'),
            (r'visit the YourPharmacy Health website', 'visit the [YourPharmacy Health website](https://yourpharmacy.example.com)'),
            
            # Store locator
            (r'https://yourpharmacy\.example\.com/locations', '[Store Locator](https://yourpharmacy.example.com/locations)'),
            
            # Generic URL detection (not already in markdown)
            (r'(?<!\[)(?<!\()https?://[\w\-._~:/?#[\]@!$&\'()*+,;=%.]+(?!\))', self._format_url),
        ]
        
    def _format_url(self, match):
        """Format a URL as markdown link"""
        url = match.group(0)
        # Extract domain for display
        domain = re.search(r'https?://([^/]+)', url)
        if domain:
            display = domain.group(1).replace('www.', '')
            return f'[{display}]({url})'
        return f'[Link]({url})'
    
    def format_response(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        Format response text with proper markdown
        
        Args:
            text: The response text to format
            context: Optional context for client-specific formatting
            
        Returns:
            Formatted text with markdown
        """
        if not text:
            return text
            
        formatted = text
        
        # Apply phone number formatting
        for pattern, replacement in self.phone_patterns:
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        
        # Apply URL formatting
        for pattern, replacement in self.url_patterns:
            if callable(replacement):
                formatted = re.sub(pattern, replacement, formatted)
            else:
                formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        
        # Ensure proper markdown formatting
        # Fix bold text
        formatted = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', formatted)
        
        # Fix lists (ensure bullets have proper spacing)
        formatted = re.sub(r'^([•\-\*])\s*', r'\1 ', formatted, flags=re.MULTILINE)
        
        return formatted
    
    def format_sources(self, sources: list) -> str:
        """
        Format source URLs as markdown links
        
        Args:
            sources: List of source URLs or filenames
            
        Returns:
            Formatted sources string
        """
        if not sources:
            return ""
        
        source_links = []
        for source in sources[:3]:  # Limit to 3 sources
            if source.startswith('www.yourpharmacy.example.com_'):
                url_path = source.replace('www.yourpharmacy.example.com_', '').replace('_', '-')
                url = f"https://www.yourpharmacy.example.com/{url_path}"
                display_name = url_path.replace('-', ' ').title()[:30]
                source_links.append(f"[{display_name}]({url})")
            elif source.startswith('yourpharmacy.example.com_'):
                url_path = source.replace('yourpharmacy.example.com_', '').replace('_', '-')
                url = f"https://yourpharmacy.example.com/{url_path}"
                display_name = url_path.replace('-', ' ').title()[:30]
                source_links.append(f"[{display_name}]({url})")
            elif source.startswith('http'):
                # Already a URL
                domain = re.search(r'https?://([^/]+)', source)
                display = domain.group(1).replace('www.', '') if domain else 'Source'
                source_links.append(f"[{display}]({source})")
            else:
                # Unknown format
                source_links.append(f"[{source}]({source})")
        
        return f"**Sources:** {' | '.join(source_links)}"

# Global formatter instance
markdown_formatter = MarkdownFormatter()