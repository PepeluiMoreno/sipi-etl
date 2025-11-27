"""
Cache Redis para geocoding
"""
from typing import Optional, List, Dict, Any
import json
import hashlib
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .geocoder import GeocodingResult
from .hybrid_geocoder import GeocoderProvider


class RedisGeocoderCache:
    """
    Cache Redis para geocoding con expiración automática
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        db: int = 0,
        ttl_days: int = 7,
        key_prefix: str = "geocoder:"
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not installed. Run: pip install redis")
        
        self.redis_url = redis_url
        self.db = db
        self.ttl = timedelta(days=ttl_days)
        self.key_prefix = key_prefix
        self.client: Optional[redis.Redis] = None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
    
    async def connect(self):
        """Conecta a Redis"""
        if self.client is None:
            self.client = await redis.from_url(
                self.redis_url,
                db=self.db,
                decode_responses=True,
                encoding='utf-8'
            )
    
    async def disconnect(self):
        """Desconecta de Redis"""
        if self.client:
            await self.client.close()
            self.client = None
    
    def _make_key(self, address: str, country: str = "ES") -> str:
        """Genera key de cache normalizada"""
        normalized = f"{address.lower().strip()}|{country.upper()}"
        hash_key = hashlib.md5(normalized.encode()).hexdigest()
        return f"{self.key_prefix}{hash_key}"
    
    async def get(
        self,
        address: str,
        country: str = "ES"
    ) -> Optional[List[GeocodingResult]]:
        """Obtiene del cache si existe"""
        if not self.client:
            await self.connect()
        
        key = self._make_key(address, country)
        
        try:
            data = await self.client.get(key)
            
            if data is None:
                self.stats['misses'] += 1
                return None
            
            # Deserializar
            cached = json.loads(data)
            results = [self._dict_to_result(r) for r in cached['results']]
            
            self.stats['hits'] += 1
            return results
        
        except Exception as e:
            self.stats['errors'] += 1
            print(f"Redis cache error (get): {e}")
            return None
    
    async def set(
        self,
        address: str,
        results: List[GeocodingResult],
        provider: GeocoderProvider,
        country: str = "ES"
    ):
        """Guarda en cache con TTL"""
        if not self.client:
            await self.connect()
        
        key = self._make_key(address, country)
        
        try:
            # Serializar
            data = {
                'results': [self._result_to_dict(r) for r in results],
                'provider': provider.value,
                'cached_at': datetime.now().isoformat()
            }
            
            # Guardar con TTL
            await self.client.setex(
                key,
                self.ttl,
                json.dumps(data)
            )
            
            self.stats['sets'] += 1
        
        except Exception as e:
            self.stats['errors'] += 1
            print(f"Redis cache error (set): {e}")
    
    async def clear(self):
        """Limpia todo el cache de geocoding"""
        if not self.client:
            await self.connect()
        
        try:
            # Buscar todas las keys con el prefijo
            pattern = f"{self.key_prefix}*"
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self.client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    await self.client.delete(*keys)
                    deleted += len(keys)
                
                if cursor == 0:
                    break
            
            return deleted
        
        except Exception as e:
            print(f"Redis cache error (clear): {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        if not self.client:
            await self.connect()
        
        try:
            info = await self.client.info('stats')
            
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (
                self.stats['hits'] / total_requests
                if total_requests > 0
                else 0
            )
            
            return {
                **self.stats,
                'hit_rate': round(hit_rate * 100, 2),
                'redis_keyspace_hits': info.get('keyspace_hits', 0),
                'redis_keyspace_misses': info.get('keyspace_misses', 0)
            }
        
        except Exception as e:
            print(f"Redis stats error: {e}")
            return self.stats
    
    @staticmethod
    def _result_to_dict(result: GeocodingResult) -> Dict:
        """Convierte GeocodingResult a dict"""
        return {
            'address': result.address,
            'display_name': result.display_name,
            'lat': result.lat,
            'lon': result.lon,
            'house_number': result.house_number,
            'road': result.road,
            'suburb': result.suburb,
            'city': result.city,
            'state': result.state,
            'postcode': result.postcode,
            'country': result.country,
            'osm_type': result.osm_type,
            'osm_id': result.osm_id,
            'place_type': result.place_type,
            'bbox': result.bbox
        }
    
    @staticmethod
    def _dict_to_result(data: Dict) -> GeocodingResult:
        """Convierte dict a GeocodingResult"""
        return GeocodingResult(**data)


# Instancia global (singleton)
_redis_cache: Optional[RedisGeocoderCache] = None


async def get_redis_cache(redis_url: str = None) -> RedisGeocoderCache:
    """
    Obtiene instancia global de Redis cache
    """
    global _redis_cache
    
    if _redis_cache is None:
        from os import getenv
        url = redis_url or getenv('REDIS_URL', 'redis://localhost:6379')
        _redis_cache = RedisGeocoderCache(redis_url=url)
        await _redis_cache.connect()
    
    return _redis_cache