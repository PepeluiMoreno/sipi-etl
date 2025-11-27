"""
Módulo de Idealista - Scraper, loader y transformaciones
"""

# Exponer el scraper para que pueda ser importado
from .extract.scraper import IdealistaScraper

__all__ = ['IdealistaScraper']