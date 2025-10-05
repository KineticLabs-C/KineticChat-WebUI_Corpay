"""
Deterministic Response Handler for KineticChat WebUI
Simplified version - only help fallback function preserved
"""

import re
from typing import Optional


class DeterministicHandler:
    """Handles basic help queries with pre-defined responses."""

    def __init__(self):
        """Initialize with minimal help response."""
        self.responses = {
            'help': {
                'en': """I'm here to help you with questions about Corpay Financial Services. I can assist with:

• Payment solutions and processing
• Corporate and virtual card information
• International payments and currency exchange
• Financial services and banking solutions

What would you like to know about Corpay?""",

                'es': """Estoy aquí para ayudarle con preguntas sobre Corpay Financial Services. Puedo ayudarle con:

• Soluciones de pago y procesamiento
• Información sobre tarjetas corporativas y virtuales
• Pagos internacionales y cambio de divisas
• Servicios financieros y soluciones bancarias

¿Sobre qué le gustaría saber acerca de Corpay?"""
            }
        }

    def get_response(self, message: str, language: str = "en") -> Optional[str]:
        """
        Get deterministic response for basic help queries.
        Returns None if query should go to RAG system.
        """

        message_lower = message.lower().strip()

        # Only respond to very specific help requests
        help_patterns = [
            'i need help', 'help me', 'can you help', 'please help',
            'help with', 'assist me', 'i need assistance'
        ]

        for pattern in help_patterns:
            if pattern in message_lower:
                return self.responses['help'].get(language, self.responses['help']['en'])

        return None  # No deterministic response found

    def requires_rag(self, message: str) -> bool:
        """
        All queries now go to RAG system except basic help.
        """
        return True