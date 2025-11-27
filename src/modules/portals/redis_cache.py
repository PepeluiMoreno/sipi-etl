"""
Cache Redis para deduplicación
"""
import redis.asyncio as redis
import os
from typing import Optional


class RedisCache:
    """
    Cliente Redis para deduplicación
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        # Por defecto usa 'redis' (nombre del servicio Docker)
        # Usar 'localhost' solo cuando se ejecuta fuera de Docker
        default_redis_host = os.getenv('REDIS_HOST', 'redis')
        default_redis_port = os.getenv('REDIS_PORT', '6379')
        default_redis_db = os.getenv('REDIS_DB', '0')
        
        self.redis_url = os.getenv(
            'REDIS_URL',
            f'redis://{default_redis_host}:{default_redis_port}/{default_redis_db}'
        )
    
    async def connect(self):
        """Conecta a Redis"""
        if self.redis is None:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def check_duplicate(
        self,
        portal: str,
        id_portal: str,
        ttl_hours: int = 24
    ) -> bool:
        """
        Verifica si un inmueble ya fue procesado
        
        Args:
            portal: Nombre del portal
            id_portal: ID del inmueble
            ttl_hours: Horas de TTL para la clave
            
        Returns:
            True si es duplicado, False si es nuevo
        """
        if not self.redis:
            return False
        
        key = f"processed:{portal}:{id_portal}"
        
        # Verificar si existe
        exists = await self.redis.exists(key)
        
        if exists:
            return True
        
        # Marcar como procesado
        await self.redis.setex(
            key,
            ttl_hours * 3600,
            "1"
        )
        
        return False
    
    async def close(self):
        """Cierra conexión"""
        if self.redis:
            await self.redis.close()