"""
Configuración de base de datos para SIPI-ETL en entorno Docker

Uso en Jupyter:
    from db_config import get_db_url
    
    db_url = get_db_url()
    # postgresql://user:password@postgis:5432/spatialdb
"""

import os
from typing import Optional


def get_db_url(
    user: Optional[str] = None,
    password: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
) -> str:
    """
    Construir URL de conexión PostgreSQL
    
    Por defecto usa los valores del docker-compose.yml:
    - user: user
    - password: password
    - host: postgis (nombre del servicio Docker)
    - port: 5432
    - database: spatialdb
    
    Args:
        user: Usuario de PostgreSQL
        password: Contraseña
        host: Host (usar 'postgis' desde Jupyter, 'localhost' desde host)
        port: Puerto
        database: Nombre de la base de datos
        
    Returns:
        URL de conexión en formato postgresql://user:pass@host:port/db
    """
    user = user or os.getenv("POSTGRES_USER", "user")
    password = password or os.getenv("POSTGRES_PASSWORD", "password")
    host = host or os.getenv("POSTGRES_HOST", "postgis")  # Nombre del servicio Docker
    port = port or int(os.getenv("POSTGRES_PORT", "5432"))
    database = database or os.getenv("POSTGRES_DB", "spatialdb")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_async_db_url(**kwargs) -> str:
    """
    URL de conexión para asyncpg (drivers asíncronos)
    
    Returns:
        URL en formato postgresql+asyncpg://
    """
    base_url = get_db_url(**kwargs)
    return base_url.replace("postgresql://", "postgresql+asyncpg://")


def get_sync_db_url(**kwargs) -> str:
    """
    URL de conexión para psycopg2 (drivers síncronos)
    
    Returns:
        URL en formato postgresql+psycopg2://
    """
    base_url = get_db_url(**kwargs)
    return base_url.replace("postgresql://", "postgresql+psycopg2://")


# Configuraciones preestablecidas
DB_CONFIG = {
    "postgis": {
        "user": "user",
        "password": "password",
        "host": "postgis",
        "port": 5432,
        "database": "spatialdb",
    },
    "postgres": {
        "user": "user",
        "password": "password",
        "host": "postgres",
        "port": 5432,
        "database": "mydb",
    },
}


def get_db_url_from_service(service: str = "postgis") -> str:
    """
    Obtener URL desde configuración preestablecida
    
    Args:
        service: 'postgis' o 'postgres'
        
    Returns:
        URL de conexión
    """
    if service not in DB_CONFIG:
        raise ValueError(f"Servicio '{service}' no encontrado. Disponibles: {list(DB_CONFIG.keys())}")
    
    config = DB_CONFIG[service]
    return get_db_url(**config)


if __name__ == "__main__":
    # Test
    print("URLs de conexión:")
    print(f"PostGIS: {get_db_url_from_service('postgis')}")
    print(f"Postgres: {get_db_url_from_service('postgres')}")
    print(f"\nAsync (asyncpg): {get_async_db_url()}")
    print(f"Sync (psycopg2): {get_sync_db_url()}")