"""
Scraper de Idealista implementando la interfaz BasePortalScraper
"""
from typing import Optional, List
import re
from urllib.parse import parse_qs, urlparse

from ..base_scraper import BasePortalScraper, InmuebleData, ScraperConfig
from ..factory import register_scraper
from ....core.etl_event_system import PortalType
from .extract.idealista_client import IdealistaClient


@register_scraper(PortalType.IDEALISTA)
class IdealistaScraper(BasePortalScraper):
    """
    Implementación del scraper para Idealista
    """
    
    def __init__(self, config: ScraperConfig = None):
        super().__init__(PortalType.IDEALISTA, config)
        self.base_url = "https://www.idealista.com"
    
    async def scrape_listado(
        self,
        provincia: Optional[str] = None,
        ciudad: Optional[str] = None,
        zona: Optional[str] = None,
        max_paginas: Optional[int] = None
    ) -> List[str]:
        """Implementación específica de Idealista"""
        await self.emit_scraping_started(
            task_name=f"Listado {provincia or ciudad or zona}",
            total_items=max_paginas
        )
        
        ids = []
        
        with IdealistaClient(headless=self.config.headless) as client:
            try:
                ids = client.scrape_listado(
                    provincia=provincia,
                    ciudad=ciudad,
                    zona=zona,
                    max_paginas=max_paginas
                )
                
                await self.emit_scraping_completed(
                    total_scraped=len(ids),
                    summary={"provincia": provincia, "ids_count": len(ids)}
                )
                
            except Exception as e:
                await self.emit_scraping_error(str(e), {"provincia": provincia})
                raise
        
        return ids
    
    async def scrape_inmueble(self, inmueble_id: str) -> Optional[InmuebleData]:
        """Implementación específica de Idealista"""
        with IdealistaClient(headless=self.config.headless) as client:
            try:
                raw_data = client.scrape_inmueble(inmueble_id)
                
                if not raw_data:
                    return None
                
                # Normalizar a estructura común
                return InmuebleData(
                    id_portal=inmueble_id,
                    portal="idealista",
                    url=raw_data['url'],
                    titulo=raw_data.get('titulo', ''),
                    descripcion=raw_data.get('descripcion'),
                    precio=raw_data.get('precio'),
                    superficie=raw_data.get('superficie'),
                    tipo=raw_data.get('tipo'),
                    localizacion=raw_data.get('localizacion', ''),
                    provincia=self._extract_provincia(raw_data.get('localizacion', '')),
                    lat=raw_data.get('lat'),
                    lon=raw_data.get('lon'),
                    caracteristicas=(
                        raw_data.get('caracteristicas_basicas', []) +
                        raw_data.get('caracteristicas_extras', [])
                    ),
                    imagenes=[],  # TODO: Implementar extracción de imágenes
                    fecha_publicacion=None,
                    scraped_at=datetime.now(),
                    raw_data=raw_data
                )
                
            except Exception as e:
                await self.emit_scraping_error(
                    str(e),
                    {"inmueble_id": inmueble_id}
                )
                return None
    
    def extract_coordinates(self, soup) -> tuple[Optional[float], Optional[float]]:
        """Extrae coordenadas del mapa de Idealista"""
        try:
            map_img = soup.find('img', {'id': 'sMap'})
            
            if not map_img or not map_img.get('src'):
                return None, None
            
            map_url = map_img['src']
            parsed = urlparse(map_url)
            params = parse_qs(parsed.query)
            
            if 'center' in params:
                center = params['center'][0]
                lat, lon = center.split(',')
                return float(lat), float(lon)
            
            if 'markers' in params:
                markers = params['markers'][0]
                coords_match = re.search(
                    r'([+-]?\d+\.\d+),([+-]?\d+\.\d+)$',
                    markers
                )
                if coords_match:
                    return float(coords_match.group(1)), float(coords_match.group(2))
        
        except Exception as e:
            print(f"Error extracting coordinates: {e}")
        
        return None, None
    
    def get_search_url(
        self,
        provincia: Optional[str] = None,
        ciudad: Optional[str] = None,
        zona: Optional[str] = None,
        pagina: int = 1
    ) -> str:
        """Construye URL de búsqueda de Idealista"""
        url_parts = [self.base_url, "venta-viviendas"]
        
        if provincia:
            url_parts.append(self.normalize_provincia(provincia))
        if ciudad and ciudad != provincia:
            url_parts.append(self.normalize_provincia(ciudad))
        if zona:
            url_parts.append(self.normalize_provincia(zona))
        
        base_url = '/'.join(url_parts) + '/'
        
        if pagina > 1:
            return f"{base_url}pagina-{pagina}.htm"
        
        return base_url
    
    def _extract_provincia(self, localizacion: str) -> str:
        """Extrae provincia de la localización"""
        # TODO: Implementar lógica más robusta
        parts = localizacion.split(',')
        return parts[-1].strip() if parts else ''