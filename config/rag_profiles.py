"""
RAG Configuration Profiles for KineticChat WebUI
Hot-swappable configuration for different RAG collections and domains
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class RAGProfile:
    """Configuration profile for a RAG collection"""
    collection_name: str
    embedding_model: str
    system_context: str
    company_name: str
    quick_topics: list
    domain_synonyms: Dict[str, list]

# Available RAG profiles - hot-swappable via environment variable
RAG_PROFILES = {
    "finance": RAGProfile(
        collection_name="kinetic_corpay_finance_rag",
        embedding_model="all-MiniLM-L6-v2",
        system_context="financial_services",
        company_name="Corpay Financial Services",
        quick_topics=["Payments", "Cards", "Solutions", "Resources"],
        domain_synonyms={
            'payments': ['payment processing', 'transaction processing', 'money transfer', 'payment solutions'],
            'cards': ['corporate cards', 'business cards', 'virtual cards', 'commercial cards'],
            'fx': ['foreign exchange', 'currency exchange', 'hedging', 'currency risk'],
            'cross_border': ['international payments', 'global payments', 'border payments', 'international transfer']
        }
    ),
    # Legacy profile for pharmacy (preserved for portfolio)
    "pharmacy": RAGProfile(
        collection_name="kinetic_KineticAgent_Pharma_Demo",
        embedding_model="all-MiniLM-L6-v2",
        system_context="healthcare",
        company_name="YourPharmacy Health",
        quick_topics=["Vaccinations", "Medications", "Services", "Locations"],
        domain_synonyms={
            'vaccines': ['vaccination', 'immunization', 'shots', 'immunize', 'vaccinate'],
            'medication': ['medicine', 'drugs', 'prescription', 'pills', 'treatment', 'therapy'],
            'pharmacy': ['pharmacist', 'prescription services', 'drug store', 'medication management'],
            'testing': ['screening', 'examination', 'checkup', 'diagnosis', 'assessment']
        }
    )
}

def get_active_profile() -> RAGProfile:
    """Get the active RAG profile based on environment variable"""
    import os
    active_profile = os.getenv("ACTIVE_RAG_PROFILE", "finance")
    if active_profile not in RAG_PROFILES:
        raise ValueError(f"Unknown RAG profile: {active_profile}. Available: {list(RAG_PROFILES.keys())}")
    return RAG_PROFILES[active_profile]

def get_profile_by_name(name: str) -> RAGProfile:
    """Get a specific RAG profile by name"""
    if name not in RAG_PROFILES:
        raise ValueError(f"Unknown RAG profile: {name}. Available: {list(RAG_PROFILES.keys())}")
    return RAG_PROFILES[name]
