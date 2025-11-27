"""
Orquestador que coordina scraping de múltiples portales en paralelo
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..modules.portals.factory import create_scraper, get_available_portals
from ..modules.portals.base_scraper import ScraperConfig
from ...core.etl_event_system import PortalType, event_bus, EventType


class MultiPortalOrchestrator:
    """
    Coordina el scraping de múltiples portales en paralelo
    """
    
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.active_tasks: Dict[PortalType, asyncio.Task] = {}
    
    async def scrape_all_portals(
        self,
        provincias: List[str],
        portals: Optional[List[PortalType]] = None
    ) -> Dict[PortalType, Dict[str, List[str]]]:
        """
        Scrape todas las provincias en todos los portales en paralelo
        
        Args:
            provincias: Lista de provincias a scrapear
            portals: Portales específicos (None = todos los disponibles)
            
        Returns:
            Dict con resultados por portal
        """
        if portals is None:
            portals = get_available_portals()
        
        # Crear tareas para cada portal
        tasks = {}
        for portal in portals:
            task = asyncio.create_task(
                self._scrape_portal(portal, provincias)
            )
            tasks[portal] = task
            self.active_tasks[portal] = task
        
        # Esperar a que todas completen
        results = {}
        for portal, task in tasks.items():
            try:
                results[portal] = await task
            except Exception as e:
                print(f"Error scraping {portal.value}: {e}")
                results[portal] = {}
            finally:
                if portal in self.active_tasks:
                    del self.active_tasks[portal]
        
        return results
    
    async def _scrape_portal(
        self,
        portal: PortalType,
        provincias: List[str]
    ) -> Dict[str, List[str]]:
        """Scrape un portal específico"""
        scraper = create_scraper(portal, self.config)
        results = {}
        
        for provincia in provincias:
            try:
                ids = await scraper.scrape_listado(provincia=provincia)
                results[provincia] = ids
            except Exception as e:
                print(f"Error scraping {provincia} in {portal.value}: {e}")
                results[provincia] = []
        
        return results
    
    async def stop_portal(self, portal: PortalType):
        """Detiene el scraping de un portal específico"""
        if portal in self.active_tasks:
            self.active_tasks[portal].cancel()
            del self.active_tasks[portal]
    
    async def stop_all(self):
        """Detiene todos los scrapers activos"""
        for task in self.active_tasks.values():
            task.cancel()
        self.active_tasks.clear()
    
    def get_active_portals(self) -> List[PortalType]:
        """Retorna lista de portales activos"""
        return list(self.active_tasks.keys())