"""
Módulo de portales inmobiliarios

Este módulo contiene los scrapers, loaders y utilidades para diferentes portales.
"""

# Importar componentes base
from .base_scraper import BasePortalScraper, ScraperConfig, InmuebleData
from .base_loader import BaseLoader, LoaderStats, PostgresConnectionPool
from .factory import create_scraper, register_scraper, get_available_portals, is_portal_supported
from .loader_factory import create_loader

# IMPORTANTE: Importar todos los scrapers para que se registren automáticamente
# El decorador @register_scraper solo se ejecuta cuando se importa el módulo
try:
    from .idealista import scraper as idealista_scraper
    print("✓ Scraper Idealista registrado")
except ImportError as e:
    print(f"⚠ No se pudo cargar scraper Idealista: {e}")

# Agregar más scrapers aquí cuando estén disponibles:
# try:
#     from .fotocasa import scraper as fotocasa_scraper
#     print("✓ Scraper Fotocasa registrado")
# except ImportError as e:
#     print(f"⚠ No se pudo cargar scraper Fotocasa: {e}")

# try:
#     from .pisos import scraper as pisos_scraper
#     print("✓ Scraper Pisos.com registrado")
# except ImportError as e:
#     print(f"⚠ No se pudo cargar scraper Pisos.com: {e}")

# try:
#     from .habitaclia import scraper as habitaclia_scraper
#     print("✓ Scraper Habitaclia registrado")
# except ImportError as e:
#     print(f"⚠ No se pudo cargar scraper Habitaclia: {e}")


__all__ = [
    # Base classes
    'BasePortalScraper',
    'ScraperConfig',
    'InmuebleData',
    'BaseLoader',
    'LoaderStats',
    'PostgresConnectionPool',
    
    # Factories
    'create_scraper',
    'register_scraper',
    'get_available_portals',
    'is_portal_supported',
    'create_loader',
]