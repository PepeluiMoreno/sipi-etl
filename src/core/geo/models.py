"""
Modelos para gestión de regiones geográficas
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal
from datetime import datetime
from enum import Enum


class RegionShape(Enum):
    """Formas de región de búsqueda"""
    CIRCLE = "circle"           # Círculo con radio
    POLYGON = "polygon"         # Polígono personalizado
    BOUNDING_BOX = "bbox"       # Rectángulo delimitador
    ADMINISTRATIVE = "admin"     # Límite administrativo (barrio, distrito, etc.)


@dataclass
class GeoRegion:
    """
    Región geográfica de interés para monitoreo
    """
    id: Optional[int] = None
    name: str = None                    # Nombre descriptivo
    shape_type: RegionShape = None
    
    # Para CIRCLE
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_m: Optional[int] = None
    
    # Para POLYGON / BOUNDING_BOX
    coordinates: Optional[List[Tuple[float, float]]] = None
    
    # Para ADMINISTRATIVE
    osm_relation_id: Optional[int] = None  # ID de relación OSM (límite administrativo)
    admin_level: Optional[int] = None      # Nivel administrativo OSM
    
    # Metadata
    address: Optional[str] = None          # Dirección original
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    # Estado de monitoreo
    is_active: bool = True
    last_checked: Optional[datetime] = None
    
    def to_wkt(self) -> str:
        """Convierte la región a formato WKT (Well-Known Text) para PostGIS"""
        if self.shape_type == RegionShape.CIRCLE:
            # PostGIS no tiene tipo CIRCLE nativo, usar buffer
            return f"POINT({self.center_lon} {self.center_lat})"
        
        elif self.shape_type == RegionShape.POLYGON:
            if not self.coordinates or len(self.coordinates) < 3:
                raise ValueError("Polygon needs at least 3 coordinates")
            
            # Cerrar el polígono si no está cerrado
            coords = self.coordinates.copy()
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            
            coords_str = ', '.join(f"{lon} {lat}" for lat, lon in coords)
            return f"POLYGON(({coords_str}))"
        
        elif self.shape_type == RegionShape.BOUNDING_BOX:
            if not self.coordinates or len(self.coordinates) != 2:
                raise ValueError("Bounding box needs exactly 2 coordinates (SW, NE)")
            
            sw_lat, sw_lon = self.coordinates[0]
            ne_lat, ne_lon = self.coordinates[1]
            
            coords_str = ', '.join([
                f"{sw_lon} {sw_lat}",
                f"{ne_lon} {sw_lat}",
                f"{ne_lon} {ne_lat}",
                f"{sw_lon} {ne_lat}",
                f"{sw_lon} {sw_lat}"  # Cerrar
            ])
            return f"POLYGON(({coords_str}))"
        
        return None
    
    def contains_point(self, lat: float, lon: float) -> bool:
        """Verifica si un punto está dentro de la región"""
        if self.shape_type == RegionShape.CIRCLE:
            from math import radians, sin, cos, sqrt, atan2
            
            # Haversine distance
            R = 6371000  # Radio de la Tierra en metros
            lat1_rad = radians(self.center_lat)
            lat2_rad = radians(lat)
            delta_lat = radians(lat - self.center_lat)
            delta_lon = radians(lon - self.center_lon)
            
            a = sin(delta_lat / 2) ** 2 + \
                cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = R * c
            
            return distance <= self.radius_m
        
        # Para POLYGON y BBOX, mejor usar PostGIS en producción
        # Aquí implementación simplificada
        return False
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """
        Retorna bounding box (min_lat, min_lon, max_lat, max_lon)
        Útil para queries eficientes
        """
        if self.shape_type == RegionShape.CIRCLE:
            # Aproximación usando 1 grado ≈ 111km
            lat_offset = (self.radius_m / 111000)
            lon_offset = (self.radius_m / (111000 * abs(cos(radians(self.center_lat)))))
            
            return (
                self.center_lat - lat_offset,
                self.center_lon - lon_offset,
                self.center_lat + lat_offset,
                self.center_lon + lon_offset
            )
        
        elif self.shape_type == RegionShape.POLYGON:
            lats = [coord[0] for coord in self.coordinates]
            lons = [coord[1] for coord in self.coordinates]
            return (min(lats), min(lons), max(lats), max(lons))
        
        elif self.shape_type == RegionShape.BOUNDING_BOX:
            sw_lat, sw_lon = self.coordinates[0]
            ne_lat, ne_lon = self.coordinates[1]
            return (sw_lat, sw_lon, ne_lat, ne_lon)
        
        return None


@dataclass
class RegionAlert:
    """
    Alerta de inmueble detectado en región monitoreada
    """
    id: Optional[int] = None
    region_id: int = None
    inmueble_id: str = None
    portal: str = None
    
    # Datos del inmueble
    titulo: str = None
    precio: Optional[float] = None
    score: float = None
    status: str = None
    
    # Ubicación
    lat: float = None
    lon: float = None
    distance_to_center_m: Optional[float] = None
    
    # OSM match
    osm_church_id: Optional[int] = None
    osm_church_name: Optional[str] = None
    osm_distance_m: Optional[float] = None
    
    # Metadata
    detected_at: datetime = None
    notified: bool = False
    notified_at: Optional[datetime] = None