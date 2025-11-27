"""
Constructor de regiones de búsqueda a partir de direcciones
"""
from typing import Optional, List, Tuple
from .models import GeoRegion, RegionShape
from .geocoder import NominatimGeocoder, PhotonGeocoder, GeocodingResult


class RegionBuilder:
    """
    Construye regiones de búsqueda a partir de direcciones
    """
    
    def __init__(self, geocoder=None):
        self.geocoder = geocoder or NominatimGeocoder()
    
    def from_address(
        self,
        address: str,
        radius_m: int = 500,
        name: Optional[str] = None
    ) -> Optional[GeoRegion]:
        """
        Crea región circular desde una dirección
        
        Args:
            address: Dirección a geocodificar
            radius_m: Radio del círculo en metros
            name: Nombre descriptivo (opcional)
            
        Returns:
            GeoRegion o None si falla el geocoding
        """
        results = self.geocoder.geocode(address, limit=1)
        
        if not results:
            print(f"No se pudo geocodificar: {address}")
            return None
        
        result = results[0]
        
        return GeoRegion(
            name=name or f"Región: {result.display_name}",
            shape_type=RegionShape.CIRCLE,
            center_lat=result.lat,
            center_lon=result.lon,
            radius_m=radius_m,
            address=address,
            description=f"Radio de {radius_m}m alrededor de {result.display_name}"
        )
    
    def from_coordinates(
        self,
        lat: float,
        lon: float,
        radius_m: int = 500,
        name: Optional[str] = None
    ) -> GeoRegion:
        """
        Crea región circular desde coordenadas
        """
        # Reverse geocoding para obtener dirección
        reverse_result = self.geocoder.reverse_geocode(lat, lon)
        
        address = reverse_result.display_name if reverse_result else f"{lat}, {lon}"
        
        return GeoRegion(
            name=name or f"Región: {address}",
            shape_type=RegionShape.CIRCLE,
            center_lat=lat,
            center_lon=lon,
            radius_m=radius_m,
            address=address,
            description=f"Radio de {radius_m}m"
        )
    
    def from_bounding_box(
        self,
        sw_lat: float,
        sw_lon: float,
        ne_lat: float,
        ne_lon: float,
        name: Optional[str] = None
    ) -> GeoRegion:
        """
        Crea región desde bounding box (rectángulo)
        
        Args:
            sw_lat, sw_lon: Esquina suroeste
            ne_lat, ne_lon: Esquina noreste
        """
        return GeoRegion(
            name=name or "Región rectangular",
            shape_type=RegionShape.BOUNDING_BOX,
            coordinates=[(sw_lat, sw_lon), (ne_lat, ne_lon)],
            description=f"Bounding box: SW({sw_lat}, {sw_lon}) NE({ne_lat}, {ne_lon})"
        )
    
    def from_polygon(
        self,
        coordinates: List[Tuple[float, float]],
        name: Optional[str] = None
    ) -> GeoRegion:
        """
        Crea región desde polígono personalizado
        
        Args:
            coordinates: Lista de tuplas (lat, lon)
        """
        if len(coordinates) < 3:
            raise ValueError("Polygon needs at least 3 points")
        
        return GeoRegion(
            name=name or "Región poligonal",
            shape_type=RegionShape.POLYGON,
            coordinates=coordinates,
            description=f"Polígono con {len(coordinates)} vértices"
        )
    
    def from_church(
        self,
        church_name: str,
        radius_m: int = 500
    ) -> Optional[GeoRegion]:
        """
        Crea región alrededor de una iglesia específica
        
        Args:
            church_name: Nombre de la iglesia
            radius_m: Radio de monitoreo
        """
        # Buscar iglesia con query específica
        query = f"{church_name} iglesia España"
        results = self.geocoder.geocode(query, limit=5)
        
        if not results:
            print(f"No se encontró: {church_name}")
            return None
        
        # Filtrar resultados que sean lugares de culto
        church_result = None
        for result in results:
            if result.place_type in ['place_of_worship', 'church', 'cathedral']:
                church_result = result
                break
        
        if not church_result:
            church_result = results[0]  # Tomar el primero si no hay coincidencia exacta
        
        return GeoRegion(
            name=f"Monitoreo: {church_result.display_name}",
            shape_type=RegionShape.CIRCLE,
            center_lat=church_result.lat,
            center_lon=church_result.lon,
            radius_m=radius_m,
            address=church_result.display_name,
            description=f"Radio de {radius_m}m alrededor de {church_result.display_name}"
        )