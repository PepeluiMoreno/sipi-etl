"""
Loader para Idealista con scoring completo
"""
from typing import Tuple, List, Optional
import asyncpg
import json

from ...base_loader import BaseLoader
from ...base_scraper import InmuebleData
from ..transform import ReligiousPropertyScorer, OverpassClient, IdealistaOSMMatcher
from src.core.config import config


class IdealistaDetectionLoader(BaseLoader):
    """
    Loader que:
    1. Evalúa en memoria (score)
    2. Si score >= threshold → guarda detección
    3. Si score < threshold → descarta
    """
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        batch_size: int = 100,
        enable_dedup: bool = True,
        enable_screenshots: bool = True
    ):
        super().__init__(
            db_pool=db_pool,
            portal='idealista',
            batch_size=batch_size,
            enable_dedup=enable_dedup
        )
        
        self.driver = None  # Se asigna externamente
        self.scorer = ReligiousPropertyScorer()
        self.overpass_client = OverpassClient()
        self.osm_matcher = IdealistaOSMMatcher()
        self.enable_screenshots = enable_screenshots
        
        self.threshold = config.scoring['detection_threshold']
    
    async def load(self, inmueble: InmuebleData) -> bool:
        """
        Pipeline:
        1. Dedup check (Redis)
        2. Calculate score (en memoria)
        3. Filter: score >= threshold?
        4. Find OSM match (si hay coordenadas)
        5. Save to PostgreSQL (TODO: implementar)
        """
        self.stats.total_processed += 1
        self.stats.evaluated += 1
        
        # 1. Dedup check
        if self.enable_dedup:
            await self._ensure_redis()
            
            if self.redis_cache:
                is_duplicate = await self.redis_cache.check_duplicate(
                    self.portal,
                    inmueble.id_portal,
                    self.dedup_ttl_hours
                )
                
                if is_duplicate:
                    self.stats.duplicates_skipped += 1
                    return False
        
        # 2. Calculate score EN MEMORIA
        score, evidences = self._calculate_score(inmueble)
        
        # 3. Filter: ¿Es candidato?
        if score < self.threshold:
            self.stats.below_threshold += 1
            return False  # DESCARTADO
        
        # 4. Find OSM match
        osm_match = None
        if inmueble.geo.lat and inmueble.geo.lon:
            osm_churches = self.overpass_client.find_churches_nearby(
                inmueble.geo.lat,
                inmueble.geo.lon,
                inmueble.geo.uncertainty_radius_m or 150
            )
            
            inmueble_dict = {
                'titulo': inmueble.titulo or '',
                'lat': inmueble.geo.lat,
                'lon': inmueble.geo.lon
            }
            
            osm_match = self.osm_matcher.find_match(inmueble_dict, osm_churches)
            
            # Ajustar score si hay match OSM
            if osm_match:
                if osm_match.confidence >= 90:
                    score = min(score + self.scorer.weights['osm_match_exact'], 100.0)
                    evidences.append(f"Match OSM exacto: {osm_match.osm_church.name}")
                else:
                    score = min(score + self.scorer.weights['osm_match_nearby'], 100.0)
                    evidences.append(f"Match OSM cercano: {osm_match.osm_church.name} ({osm_match.osm_church.distance:.0f}m)")
        
        # 5. TODO: Guardar en BD (por ahora solo contamos)
        self.stats.new_insertions += 1
        
        # Log
        osm_info = f" [OSM: {osm_match.osm_church.name}]" if osm_match else ""
        print(f"✓ Detectado{osm_info}: {inmueble.titulo[:50]} (score: {score:.2f})")
        
        return True
    
    def _calculate_score(self, inmueble: InmuebleData) -> Tuple[float, List[str]]:
        """Calcula score en memoria"""
        inmueble_dict = {
            'titulo': inmueble.titulo or '',
            'descripcion': inmueble.descripcion or '',
            'tipo': inmueble.tipo,
            'superficie': inmueble.superficie,
            'lat': inmueble.geo.lat,
            'lon': inmueble.geo.lon,
            'geo_type': inmueble.geo.type.value,
            'uncertainty_radius_m': inmueble.geo.uncertainty_radius_m,
            'caracteristicas_basicas': inmueble.caracteristicas or [],
            'caracteristicas_extras': []
        }
        
        return self.scorer.score(inmueble_dict)