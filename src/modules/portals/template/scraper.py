"""
Template para implementar un nuevo portal
Copiar este archivo y reemplazar PORTAL_NAME con el nombre del portal
"""
from typing import Optional, List

from ..base_scraper import BasePortalScraper, InmuebleData, ScraperConfig
from ..factory import register_scraper
from ....core.etl_event_system import PortalType


@register_scraper(PortalType.PORTAL_NAME)  # Reemplazar PORTAL_NAME
class PortalNameScraper(BasePortalScraper):
    """
    Scraper para PORTAL_NAME
    """
    
    def __init__(self, config: ScraperConfig = None):
        super().__init__(PortalType.PORTAL_NAME, config)
        self.base_url = "https://www.PORTAL_NAME.com"  # URL base del portal
    
    async def scrape_listado(
        self,
        provincia: Optional[str] = None,
        ciudad: Optional[str] = None,
        zona: Optional[str] = None,
        max_paginas: Optional[int] = None
    ) -> List[str]:
        """
        TODO: Implementar lógica de scraping de listados
        
        1. Construir URL de búsqueda
        2. Iterar por páginas
        3. Extraer IDs de inmuebles
        4. Emitir eventos de progreso
        5. Retornar lista de IDs
        """
        await self.emit_scraping_started(f"Scraping {provincia}")
        
        # TODO: Implementar
        ids = []
        
        await self.emit_scraping_completed(len(ids))
        return ids
    
    async def scrape_inmueble(self, inmueble_id: str) -> Optional[InmuebleData]:
        """
        TODO: Implementar scraping de inmueble individual
        
        1. Construir URL del inmueble
        2. Obtener HTML
        3. Extraer datos
        4. Normalizar a InmuebleData
        5. Retornar
        """
        # TODO: Implementar
        return None
    
    def extract_coordinates(self, soup) -> tuple[Optional[float], Optional[float]]:
        """
        TODO: Implementar extracción de coordenadas
        
        Cada portal muestra mapas de forma diferente:
        - Idealista: Google Maps estático en <img id="sMap">
        - Fotocasa: Puede ser diferente
        - etc.
        """
        # TODO: Implementar
        return None, None
    
    def get_search_url(
        self,
        provincia: Optional[str] = None,
        ciudad: Optional[str] = None,
        zona: Optional[str] = None,
        pagina: int = 1
    ) -> str:
        """
        TODO: Construir URL de búsqueda según formato del portal
        
        Ejemplo Idealista:
        https://www.idealista.com/venta-viviendas/sevilla/
        https://www.idealista.com/venta-viviendas/sevilla/pagina-2.htm
        """
        # TODO: Implementar
        return self.base_url