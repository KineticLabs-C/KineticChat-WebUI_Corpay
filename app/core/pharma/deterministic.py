"""
Deterministic Response Handler for KineticChat WebUI
Clean room implementation based on observed behavior patterns
"""

import re
import difflib
from typing import Optional, Dict, List
from functools import lru_cache


class DeterministicHandler:
    """Handles common queries with pre-defined responses for instant answers."""
    
    def __init__(self):
        """Initialize with response templates based on observed patterns."""
        self.responses = self._init_responses()
        self.patterns = self._init_patterns()
    
    def _init_responses(self) -> Dict[str, Dict[str, str]]:
        """Initialize response templates based on observed behavior."""
        return {
            'greeting': {
                'en': "Hello! I'm your YourPharmacy Health Assistant. I can help you with information about vaccinations, medications, health screenings, and wellness services. How can I assist you today?",
                'es': "¡Hola! Soy su Asistente de Salud de YourPharmacy. Puedo ayudarle con información sobre vacunas, medicamentos, exámenes de salud y servicios de bienestar. ¿Cómo puedo ayudarle hoy?"
            },
            
            'hours': {
                'en': """**Customer Service Hours:**
• Monday-Friday: 7 a.m. - Midnight EST
• Saturday-Sunday: 7 a.m. - 9:30 p.m. EST

*Note: Individual pharmacy hours may vary by location. Check your local store for specific hours.*""",
                
                'es': """**Horario de Servicio al Cliente:**
• Lunes-Viernes: 7 a.m. - Medianoche EST
• Sábado-Domingo: 7 a.m. - 9:30 p.m. EST

*Nota: Los horarios de farmacia individuales pueden variar por ubicación.*"""
            },
            
            'location': {
                'en': """Find your nearest YourPharmacy location:
📍 **Store Locator:** [yourpharmacy.example.com/locations](https://yourpharmacy.example.com/locations)
📱 **Open in Maps:** [Find nearby](https://www.google.com/maps/search/?api=1&query=pharmacy+near+me)

With numerous locations across multiple states, there's likely a YourPharmacy near you!""",
                
                'es': """Encuentre su farmacia YourPharmacy más cercana:
📍 **Localizador de tiendas:** [yourpharmacy.example.com/tiendas](https://yourpharmacy.example.com/locations)
📱 **Abrir en Mapas:** [Buscar cerca](https://www.google.com/maps/search/?api=1&query=pharmacy+near+me)

¡Con numerosas ubicaciones en múltiples estados!"""
            },
            
            'phone': {
                'en': """You can reach YourPharmacy Health at:
📞 **Customer Service:** [1-844-708-1821](tel:18447081821)

**Available:**
• Mon, Wed & Fri: 9 AM - 5:30 PM EST
• Tue & Thu: 10 AM - 6:30 PM EST

For pharmacy-specific questions, contact your local YourPharmacy directly.""",
                
                'es': """Puede comunicarse con YourPharmacy Health al:
📞 **Servicio al Cliente:** [1-844-708-1821](tel:18447081821)

**Disponible:**
• Lun, Mié y Vie: 9 AM - 5:30 PM EST
• Mar y Jue: 10 AM - 6:30 PM EST"""
            },
            
            'insurance': {
                'en': """We accept most insurance plans and prescription discount cards:

• Medicare Part D
• Medicaid
• Most commercial insurance plans
• Prescription discount cards

For specific coverage questions, please contact your local pharmacy or visit:
[Insurance & Savings](https://yourpharmacy.example.com/insurance-savings)""",
                
                'es': """Aceptamos la mayoría de planes de seguro:

• Medicare Parte D
• Medicaid
• La mayoría de planes comerciales
• Tarjetas de descuento

Para preguntas específicas, contacte su farmacia local."""
            },
            
            'services': {
                'en': """I can help you with information about YourPharmacy Health services based on content from the YourPharmacy Health website. Here are the main topics I can assist with:

🩹 **Health Services:**
• Vaccinations & immunizations (COVID-19, flu shots, routine vaccines)
• Health screenings & testing (biometric screenings, physicals, COVID testing)
• Medication services & pharmacy support (medication optimization, prescription management)

🥗 **Wellness Programs:**
• Food as Medicine programs (nutrition counseling, food prescriptions)
• Wellness screenings and preventive care services

🏥 **Healthcare Organizations:**
• 340B pharmacy solutions and contract services
• Clinical trial opportunities and research partnerships
• Business and community health partnerships

📋 **Policies & Information:**
• Privacy policies and HIPAA information
• Terms and conditions
• Contact information and locations (numerous pharmacies and clinics across multiple states)

📞 **How to Get Started:**
• Service requests and scheduling
• Insurance coverage questions
• Pricing and business partnerships

For specific questions about any of these topics, just ask! For example:
- "Tell me about COVID vaccines"
- "What screenings do you offer?"
- "How does medication optimization work?"
- "What is Food as Medicine?"

If you need immediate assistance or want to schedule services, you can contact YourPharmacy Health directly at 1-844-708-1821 or visit https://yourpharmacy.example.com.""",
                
                'es': """Puedo ayudarte con información sobre los servicios de YourPharmacy Health basada en el contenido del sitio web de YourPharmacy Health. Estos son los temas principales en los que puedo asistirte:

🩹 **Servicios de Salud:**
• Vacunas e inmunizaciones (COVID-19, vacunas contra la gripe, vacunas de rutina)
• Exámenes de salud y pruebas (exámenes biométricos, exámenes físicos, pruebas de COVID)
• Servicios de medicamentos y apoyo farmacéutico (optimización de medicamentos, manejo de recetas)

🥗 **Programas de Bienestar:**
• Programas de Comida como Medicina (asesoramiento nutricional, recetas de alimentos)
• Exámenes de bienestar y servicios de atención preventiva

🏥 **Organizaciones de Salud:**
• Soluciones de farmacia 340B y servicios por contrato
• Oportunidades de ensayos clínicos y asociaciones de investigación
• Asociaciones de salud empresarial y comunitaria

📋 **Políticas e Información:**
• Políticas de privacidad e información HIPAA
• Términos y condiciones
• Información de contacto y ubicaciones (numerosas farmacias y clínicas en múltiples estados)

📞 **Cómo Empezar:**
• Solicitudes de servicio y programación
• Preguntas sobre cobertura de seguro
• Precios y asociaciones empresariales

Para preguntas específicas sobre cualquiera de estos temas, ¡solo pregunta! Por ejemplo:
- "Háblame sobre las vacunas COVID"
- "¿Qué exámenes ofrecen?"
- "¿Cómo funciona la optimización de medicamentos?"
- "¿Qué es Comida como Medicina?"

Si necesitas asistencia inmediata o quieres programar servicios, puedes contactar a YourPharmacy Health directamente al 1-844-708-1821 o visitar https://yourpharmacy.example.com."""
            },
            
            'help': {
                'en': """I can help you with:
• Vaccination information and scheduling
• Pharmacy hours and locations
• Prescription and medication questions
• Health screenings and wellness programs
• Insurance and payment information

What would you like to know about?""",
                
                'es': """Puedo ayudarle con:
• Información sobre vacunas
• Horarios y ubicaciones de farmacias
• Preguntas sobre medicamentos
• Exámenes de salud y programas de bienestar
• Información sobre seguros

¿Qué le gustaría saber?"""
            }
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching (handles Spanish and English)."""
        # Convert to lowercase first
        text = text.lower().strip()
        
        # Remove leading/trailing punctuation (Spanish ¿? ¡! and English ?!)
        text = text.strip('¿?¡!.,;:')
        
        # Replace accented characters
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _fuzzy_match(self, query: str, pattern: str, threshold: float = 0.75) -> bool:
        """
        Fuzzy matching with typo tolerance.
        
        Args:
            query: User's query (already normalized)
            pattern: Pattern to match against (already normalized)
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            True if similarity exceeds threshold
        """
        # Direct containment check
        if pattern in query:
            return True
        
        # Word-level subset matching
        query_words = set(query.split())
        pattern_words = set(pattern.split())
        
        if pattern_words.issubset(query_words):
            return True
        
        # Check if all key words from pattern are in query
        key_words = [w for w in pattern_words if len(w) > 3]  # Skip short words
        if key_words and all(any(w in qw for qw in query_words) for w in key_words):
            return True
        
        # Full string similarity
        similarity = difflib.SequenceMatcher(None, query, pattern).ratio()
        
        return similarity >= threshold
    
    def _init_patterns(self) -> Dict[str, List[str]]:
        """Initialize query patterns for matching."""
        return {
            'greeting': [
                r'\b(hello|hi|hey|greetings|good morning|good afternoon|good evening)\b',
                r'\b(hola|buenos dias|buenas tardes|buenas noches)\b'
            ],
            'hours': [
                r'\b(hours|open|close|closing|when are you|business hours)\b',
                r'\b(horario|abierto|cerrado|cuando abren)\b'
            ],
            'location': [
                r'\b(where|location|address|find|nearest|near me)\b.*\b(pharmacy|yourpharmacy|store)\b',
                r'\b(pharmacy|yourpharmacy|store)\b.*\b(near|location|where|address)\b',
                r'\b(donde|ubicacion|direccion|encontrar|cerca)\b'
            ],
            'phone': [
                r'\b(phone|call|telephone|contact|number)\b',
                r'\b(telefono|llamar|contacto|numero)\b'
            ],
            'insurance': [
                r'\b(insurance|medicare|medicaid|coverage|copay|cost)\b',
                r'\b(seguro|cobertura|copago|costo|precio)\b'
            ],
            'services': [
                r'\b(what services|what do you|what can you|services available)\b',
                r'\b(que servicios|que ofrece|como puede ayudar)\b'
            ],
            'help': [
                r'\b(help|assist|support|what can)\b',
                r'\b(ayuda|asistencia|apoyo|que puede)\b'
            ]
        }
    
    @lru_cache(maxsize=128)
    def get_response(self, query: str, language: str = 'en') -> Optional[str]:
        """
        Get deterministic response if query matches known patterns.
        CRITICAL ORDER: Location → RAG check → Other patterns
        
        Args:
            query: User's query
            language: Language code ('en' or 'es')
            
        Returns:
            Response string if match found, None otherwise
        """
        # Normalize query for better matching
        normalized_query = self._normalize_text(query)
        
        # STEP 1: Check LOCATION patterns FIRST (highest priority)
        location_phrases = [
            # English
            'where are you', 'where is', 'location', 'address', 'find',
            'nearest', 'near me', 'pharmacy near', 'yourpharmacy near',
            # Spanish (normalized)
            'donde esta', 'donde queda', 'ubicacion', 'direccion',
            'farmacia cerca', 'encontrar farmacia', 'mas cercana'
        ]
        
        for phrase in location_phrases:
            if self._fuzzy_match(normalized_query, phrase):
                return self.responses['location'].get(language, self.responses['location']['en'])
        
        # STEP 2: Check if query requires RAG (return None to let RAG handle it)
        if self.requires_rag(query):
            return None
        
        # STEP 3: Check other deterministic patterns
        # Check GREETING patterns
        greeting_phrases = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon',
            'hola', 'buenos dias', 'buenas tardes'
        ]
        for phrase in greeting_phrases:
            if self._fuzzy_match(normalized_query, phrase, 0.7):
                return self.responses['greeting'].get(language, self.responses['greeting']['en'])
        
        # Check HOURS patterns
        hours_phrases = [
            'hours', 'when open', 'when close', 'opening time', 'closing time',
            'horario', 'cuando abren', 'cuando cierran', 'hora de apertura'
        ]
        for phrase in hours_phrases:
            if self._fuzzy_match(normalized_query, phrase):
                return self.responses['hours'].get(language, self.responses['hours']['en'])
        
        # Check PHONE patterns
        phone_phrases = [
            'phone', 'call', 'telephone', 'contact number',
            'telefono', 'llamar', 'numero de contacto'
        ]
        for phrase in phone_phrases:
            if self._fuzzy_match(normalized_query, phrase):
                return self.responses['phone'].get(language, self.responses['phone']['en'])
        
        # Check INSURANCE patterns
        insurance_phrases = [
            'insurance', 'medicare', 'medicaid', 'coverage', 'copay',
            'seguro', 'cobertura', 'copago'
        ]
        for phrase in insurance_phrases:
            if self._fuzzy_match(normalized_query, phrase):
                return self.responses['insurance'].get(language, self.responses['insurance']['en'])
        
        # Check SERVICES/CAPABILITY patterns - match capability questions
        services_phrases = [
            'what can you help', 'what services', 'what can you', 'what do you offer',
            'how can you help', 'what can i ask', 'what topics', 'what information',
            'que servicios', 'que ofrece', 'como puede ayudar', 'que puede hacer'
        ]
        for phrase in services_phrases:
            if self._fuzzy_match(normalized_query, phrase):
                return self.responses['services'].get(language, self.responses['services']['en'])
        
        # Check HELP patterns - only for very specific help requests
        # Removed generic 'help' to avoid catching capability questions
        help_phrases = [
            'i need help with', 'help me with', 'can you assist',
            'necesito ayuda con', 'ayudame con'
        ]
        for phrase in help_phrases:
            if self._fuzzy_match(normalized_query, phrase, 0.85):
                return self.responses['help'].get(language, self.responses['help']['en'])
        
        # No deterministic match found
        return None
    
    def requires_rag(self, query: str) -> bool:
        """
        Check if query requires RAG for detailed response.
        Based on observed patterns that need specific knowledge.
        """
        rag_keywords = [
            # Specific medical queries
            'vaccine', 'vaccination', 'covid', 'flu', 'shot',
            'medication', 'prescription', 'drug', 'medicine',
            'screening', 'test', 'exam', 'blood', 'glucose',
            'wellness', 'nutrition', 'diet', 'diabetes',
            '340b', 'clinical trial',
            # Spanish equivalents
            'vacuna', 'medicamento', 'receta', 'medicina',
            'examen', 'prueba', 'bienestar', 'nutricion',
            # Question patterns that need detailed info
            'how does', 'how do', 'explain', 'tell me about', 'what is',
            'como funciona', 'explicar', 'que es'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in rag_keywords)