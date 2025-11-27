"""
Servicio de geocoding usando Nominatim (OpenStreetMap)
"""
from typing import Optional, List, Dict, Any
import requests
from time import sleep
from dataclasses import dataclass


@dataclass
class GeocodingResult:
    """Resultado de geocoding"""
    address: str
    display_name: str
    lat: float
    lon: float
    
    # Componentes de dirección
    house_number: Optional[str] = None
    road: Optional[str] = None
    suburb: Optional[str] = None  # Barrio
    city: Optional[str] = None
    state: Optional[str] = None  # Provincia/Comunidad
    postcode: Optional[str] = None
    country: Optional[str] = None
    
    # OSM metadata
    osm_type: Optional[str] = None
    osm_id: Optional[int] = None
    place_type: Optional[str] = None  # 'building', 'amenity', etc.
    
    # Bounding box
    bbox: Optional[List[float]] = None  # [min_lon, max_lon, min_lat, max_lat]
    
    # Raw data
    raw: Optional[Dict[str, Any]] = None


class NominatimGeocoder:
    """
    Geocoder usando Nominatim (OSM)
    Respetuoso con rate limits de OSM
    """
    
    def __init__(self, user_agent: str = "SIPI-ETL/1.0"):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.user_agent = user_agent
        self.rate_limit_delay = 1.0  # 1 segundo entre requests (política OSM)
    
    def geocode(
        self,
        address: str,
        country: str = "ES",
        limit: int = 1
    ) -> Optional[List[GeocodingResult]]:
        """
        Convierte dirección a coordenadas
        
        Args:
            address: Dirección a geocodificar
            country: Código de país (ISO 3166-1 alpha-2)
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados ordenados por relevancia
        """
        params = {
            'q': address,
            'format': 'json',
            'addressdetails': 1,
            'limit': limit,
            'countrycodes': country.lower()
        }
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            results = []
            for item in response.json():
                address_parts = item.get('address', {})
                
                result = GeocodingResult(
                    address=address,
                    display_name=item.get('display_name'),
                    lat=float(item.get('lat')),
                    lon=float(item.get('lon')),
                    house_number=address_parts.get('house_number'),
                    road=address_parts.get('road'),
                    suburb=address_parts.get('suburb') or address_parts.get('neighbourhood'),
                    city=address_parts.get('city') or address_parts.get('town') or address_parts.get('village'),
                    state=address_parts.get('state'),
                    postcode=address_parts.get('postcode'),
                    country=address_parts.get('country'),
                    osm_type=item.get('osm_type'),
                    osm_id=item.get('osm_id'),
                    place_type=item.get('type'),
                    bbox=item.get('boundingbox'),
                    raw=item
                )
                results.append(result)
            
            # Respetar rate limit
            sleep(self.rate_limit_delay)
            
            return results if results else None
        
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
    
    def reverse_geocode(
        self,
        lat: float,
        lon: float
    ) -> Optional[GeocodingResult]:
        """
        Convierte coordenadas a dirección
        """
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/reverse",
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            item = response.json()
            address_parts = item.get('address', {})
            
            result = GeocodingResult(
                address=item.get('display_name'),
                display_name=item.get('display_name'),
                lat=float(item.get('lat')),
                lon=float(item.get('lon')),
                house_number=address_parts.get('house_number'),
                road=address_parts.get('road'),
                suburb=address_parts.get('suburb') or address_parts.get('neighbourhood'),
                city=address_parts.get('city') or address_parts.get('town'),
                state=address_parts.get('state'),
                postcode=address_parts.get('postcode'),
                country=address_parts.get('country'),
                osm_type=item.get('osm_type'),
                osm_id=item.get('osm_id'),
                place_type=item.get('type'),
                bbox=item.get('boundingbox'),
                raw=item
            )
            
            sleep(self.rate_limit_delay)
            
            return result
        
        except Exception as e:
            print(f"Reverse geocoding error: {e}")
            return None


class PhotonGeocoder:
    """
    Geocoder usando Photon (alternativa más rápida, sin rate limits)
    https://photon.komoot.io
    """
    
    def __init__(self):
        self.base_url = "https://photon.komoot.io"
    
    def geocode(
        self,
        address: str,
        country: str = "ES",
        limit: int = 1
    ) -> Optional[List[GeocodingResult]]:
        """
        Geocoding con Photon (más rápido, sin rate limits estrictos)
        """
        params = {
            'q': address,
            'limit': limit,
            'lang': 'es'
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/api/",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                coords = feature.get('geometry', {}).get('coordinates', [])
                
                if len(coords) != 2:
                    continue
                
                lon, lat = coords
                
                result = GeocodingResult(
                    address=address,
                    display_name=props.get('name'),
                    lat=lat,
                    lon=lon,
                    house_number=props.get('housenumber'),
                    road=props.get('street'),
                    suburb=props.get('district'),
                    city=props.get('city'),
                    state=props.get('state'),
                    postcode=props.get('postcode'),
                    country=props.get('country'),
                    osm_type=props.get('osm_type'),
                    osm_id=props.get('osm_id'),
                    place_type=props.get('type'),
                    raw=feature
                )
                results.append(result)
            
            return results if results else None
        
        except Exception as e:
            print(f"Photon geocoding error: {e}")
            return None