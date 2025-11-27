"""
Módulo de extracción de Idealista
Contiene los scrapers y clientes para obtener datos de Idealista
"""

# Exponer el scraper principal
from .scraper import IdealistaScraper
from .idealista_client import IdealistaClient

__all__ = ['IdealistaScraper','IdealistaClient']