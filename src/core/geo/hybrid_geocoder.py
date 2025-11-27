"""
Geocoder híbrido con Redis cache
"""
from typing import Optional
from .redis_cache import RedisGeocoderCache, get_redis_cache


class HybridGeocoder:
    """
    Geocoder inteligente con Redis cache
    """
    
    def __init__(
        self,
        strategy: GeocoderStrategy = GeocoderStrategy.BALANCED,
        use_redis: bool = True,
        redis_url: Optional[str] = None
    ):
        self.strategy = strategy
        self.use_redis = use_redis
        self.redis_cache: Optional[RedisGeocoderCache] = None
        self.redis_url = redis_url
        
        # Fallback in-memory cache
        self.memory_cache = InMemoryCache()
        
        # Inicializar proveedores
        self.photon = PhotonGeocoder()
        self.nominatim = NominatimGeocoder()
        
        # Rate limiting
        self._last_nominatim_call = datetime.min
        self._nominatim_delay = 1.0
    
    async def _ensure_redis_connected(self):
        """Asegura que Redis está conectado"""
        if self.use_redis and self.redis_cache is None:
            try:
                self.redis_cache = await get_redis_cache(self.redis_url)
            except Exception as e:
                print(f"Redis connection failed, using memory cache: {e}")
                self.use_redis = False
    
    async def geocode(
        self,
        address: str,
        country: str = "ES",
        limit: int = 1,
        strategy: Optional[GeocoderStrategy] = None
    ) -> Optional[List[GeocodingResult]]:
        """
        Geocodifica usando Redis cache primero
        """
        strategy = strategy or self.strategy
        
        # 1. Intentar Redis cache
        if self.use_redis:
            await self._ensure_redis_connected()
            
            if self.redis_cache:
                cached = await self.redis_cache.get(address, country)
                if cached:
                    return cached[:limit]
        
        # 2. Fallback a memoria
        cached = self.memory_cache.get(address, country)
        if cached:
            return cached[:limit]
        
        # 3. Si es CACHED_ONLY, retornar None
        if strategy == GeocoderStrategy.CACHED_ONLY:
            return None
        
        # 4. Aplicar estrategia de geocoding
        results = None
        provider = None
        
        if strategy == GeocoderStrategy.FAST:
            results = self.photon.geocode(address, country, limit)
            provider = GeocoderProvider.PHOTON
        
        elif strategy == GeocoderStrategy.BALANCED:
            results = await self._geocode_balanced(address, country, limit)
            provider = GeocoderProvider.PHOTON if results else GeocoderProvider.NOMINATIM
        
        elif strategy == GeocoderStrategy.PRECISE:
            results = await self._geocode_precise(address, country, limit)
            provider = self._identify_provider(results[0]) if results else None
        
        # 5. Guardar en cache
        if results:
            # Redis
            if self.use_redis and self.redis_cache:
                await self.redis_cache.set(address, results, provider, country)
            
            # Memoria (fallback)
            self.memory_cache.set(address, results, provider, country)
        
        return results
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        stats = {}
        
        # Redis stats
        if self.use_redis and self.redis_cache:
            stats['redis'] = await self.redis_cache.get_stats()
        
        # Memory stats
        stats['memory'] = self.memory_cache.get_stats()
        
        return stats
    
    async def clear_cache(self):
        """Limpia todos los caches"""
        # Redis
        if self.use_redis and self.redis_cache:
            await self.redis_cache.clear()
        
        # Memoria
        self.memory_cache.clear()