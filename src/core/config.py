"""
Configuración global del proyecto SIPI-ETL
"""
import os
from typing import Dict, Any
from pathlib import Path


class Config:
    """Configuración centralizada"""
    
    def __init__(self):
        # Paths
        self.project_root = Path(__file__).parent.parent.parent
        self.data_path = self.project_root / "data"
        self.screenshots_path = self.data_path / "screenshots"
        self.logs_path = self.project_root / "logs"
        
        # Crear directorios si no existen
        self.screenshots_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        # Database
        self.database = {
            'url': os.getenv('DATABASE_URL', 'postgresql://sipi:sipi@localhost:5432/sipi'),
            'min_pool_size': int(os.getenv('DB_MIN_POOL_SIZE', '2')),
            'max_pool_size': int(os.getenv('DB_MAX_POOL_SIZE', '10')),
            'command_timeout': int(os.getenv('DB_COMMAND_TIMEOUT', '60'))
        }
        
        # Redis
        self.redis = {
            'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
            'enabled': os.getenv('REDIS_ENABLED', 'true').lower() == 'true'
        }
        
        # Scoring
        self.scoring = {
            'detection_threshold': float(os.getenv('DETECTION_THRESHOLD', '50.0')),
            'keywords_high': [
                'iglesia', 'convento', 'monasterio', 'capilla',
                'ermita', 'basílica', 'catedral', 'templo',
                'parroquia', 'santuario', 'claustro', 'abadía',
                'colegiata', 'priorato', 'cartuja'
            ],
            'keywords_medium': [
                'religioso', 'eclesiástico', 'sacro', 'culto',
                'episcopal', 'diocesano', 'parroquial', 'conventual',
                'monástico', 'clerical'
            ],
            'keywords_low': [
                'altar', 'campanario', 'torre', 'sacristía',
                'presbiterio', 'nave', 'crucero', 'retablo',
                'baptisterio', 'coro', 'cripta', 'ábside'
            ],
            'weights': {
                'keyword_high_title': 30.0,
                'keyword_high_description': 20.0,
                'keyword_medium': 10.0,
                'keyword_low': 5.0,
                'superficie_grande': 10.0,
                'tipo_edificio': 10.0,
                'osm_match_exact': 30.0,
                'osm_match_nearby': 15.0
            }
        }
        
        # Scraping
        self.scraping = {
            'default_max_pages': int(os.getenv('DEFAULT_MAX_PAGES', '5')),
            'request_timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'rate_limit_delay': float(os.getenv('RATE_LIMIT_DELAY', '2.0')),
            'user_agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        }
        
        # Screenshots
        self.screenshots = {
            'enabled': os.getenv('SCREENSHOTS_ENABLED', 'true').lower() == 'true',
            'format': os.getenv('SCREENSHOT_FORMAT', 'png'),
            'quality': int(os.getenv('SCREENSHOT_QUALITY', '85')),
            'max_height': int(os.getenv('SCREENSHOT_MAX_HEIGHT', '10000'))
        }
        
        # Deduplication
        self.dedup = {
            'enabled': os.getenv('DEDUP_ENABLED', 'true').lower() == 'true',
            'ttl_hours': int(os.getenv('DEDUP_TTL_HOURS', '24'))
        }
        
        # OSM/Overpass
        self.osm = {
            'overpass_url': os.getenv('OVERPASS_URL', 'https://overpass-api.de/api/interpreter'),
            'default_search_radius_m': int(os.getenv('OSM_SEARCH_RADIUS', '150')),
            'timeout': int(os.getenv('OSM_TIMEOUT', '30'))
        }


# Singleton global
config = Config()