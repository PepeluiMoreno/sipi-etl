"""
Sistema de monitoreo de regiones geográficas
Detecta automáticamente inmuebles religiosos en áreas de interés
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload

from .models import GeoRegion, RegionAlert, RegionShape
from .region_builder import RegionBuilder
from .hybrid_geocoder import get_geocoder
from ...modules.portals.config import common_config
from ...modules.portals.idealista.transform import ReligiousPropertyScorer
from ...modules.portals.idealista.extract import OverpassClient


class RegionMonitor:
    """
    Monitorea regiones geográficas y detecta inmuebles religiosos
    Funciona con TODOS los portales (schema unificado)
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.scorer = ReligiousPropertyScorer()
        self.overpass = OverpassClient()
        self.region_builder = RegionBuilder()
        self.active_monitors: Dict[int, asyncio.Task] = {}
        self.config = common_config
    
    # ========================================================================
    # Creación de regiones
    # ========================================================================
    
    async def create_region_from_address(
        self,
        address: str,
        radius_m: int = 500,
        name: Optional[str] = None,
        description: Optional[str] = None,
        auto_start: bool = True
    ) -> Optional[GeoRegion]:
        """
        Crea una región de monitoreo desde una dirección
        
        Args:
            address: Dirección del centro
            radius_m: Radio de monitoreo en metros
            name: Nombre descriptivo
            description: Descripción adicional
            auto_start: Si True, inicia monitoreo automáticamente
            
        Returns:
            GeoRegion creada y guardada en BD
        """
        # Construir región
        region = self.region_builder.from_address(address, radius_m, name)
        
        if not region:
            return None
        
        if description:
            region.description = description
        
        # Guardar en BD
        region_saved = await self._save_region(region)
        
        # Hacer scan inicial
        await self.scan_region(region_saved.id)
        
        # Iniciar monitoreo continuo si se solicita
        if auto_start:
            await self.start_monitoring(region_saved.id)
        
        return region_saved
    
    async def create_region_from_church(
        self,
        church_name: str,
        radius_m: int = 500,
        auto_start: bool = True
    ) -> Optional[GeoRegion]:
        """
        Crea región de monitoreo alrededor de una iglesia
        
        Args:
            church_name: Nombre de la iglesia
            radius_m: Radio de monitoreo
            auto_start: Iniciar monitoreo automático
        """
        region = self.region_builder.from_church(church_name, radius_m)
        
        if not region:
            return None
        
        region_saved = await self._save_region(region)
        await self.scan_region(region_saved.id)
        
        if auto_start:
            await self.start_monitoring(region_saved.id)
        
        return region_saved
    
    async def create_region_from_polygon(
        self,
        coordinates: List[Tuple[float, float]],
        name: str,
        description: Optional[str] = None,
        auto_start: bool = True
    ) -> Optional[GeoRegion]:
        """
        Crea región de monitoreo con polígono personalizado
        
        Args:
            coordinates: Lista de (lat, lon) que definen el polígono
            name: Nombre de la región
            description: Descripción
            auto_start: Iniciar monitoreo automático
        """
        region = self.region_builder.from_polygon(coordinates, name)
        region.description = description
        
        region_saved = await self._save_region(region)
        await self.scan_region(region_saved.id)
        
        if auto_start:
            await self.start_monitoring(region_saved.id)
        
        return region_saved
    
    async def create_region_from_bounding_box(
        self,
        sw_lat: float,
        sw_lon: float,
        ne_lat: float,
        ne_lon: float,
        name: str,
        description: Optional[str] = None,
        auto_start: bool = True
    ) -> GeoRegion:
        """
        Crea región rectangular (bounding box)
        
        Args:
            sw_lat, sw_lon: Esquina suroeste
            ne_lat, ne_lon: Esquina noreste
            name: Nombre de la región
        """
        region = self.region_builder.from_bounding_box(
            sw_lat, sw_lon, ne_lat, ne_lon, name
        )
        region.description = description
        
        region_saved = await self._save_region(region)
        await self.scan_region(region_saved.id)
        
        if auto_start:
            await self.start_monitoring(region_saved.id)
        
        return region_saved
    
    # ========================================================================
    # Scanning de regiones
    # ========================================================================
    
    async def scan_region(self, region_id: int) -> List[RegionAlert]:
        """
        Escanea una región buscando inmuebles religiosos
        Busca en TODOS los portales (schema unificado)
        
        Returns:
            Lista de alertas generadas
        """
        # Obtener región
        region = await self._get_region(region_id)
        
        if not region:
            raise ValueError(f"Region {region_id} not found")
        
        # Obtener bounding box para query eficiente
        bbox = region.get_bounding_box()
        
        if not bbox:
            raise ValueError(f"Cannot compute bounding box for region {region_id}")
        
        min_lat, min_lon, max_lat, max_lon = bbox
        
        # Query: Buscar inmuebles activos dentro del bounding box
        # Usa la tabla unificada portals.inmuebles_raw
        query = text("""
            SELECT 
                i.id,
                i.portal,
                i.id_portal,
                i.titulo,
                i.descripcion,
                i.precio,
                i.lat,
                i.lon,
                i.geo_type,
                i.caracteristicas,
                d.score,
                d.status,
                d.evidences,
                d.osm_match_id,
                d.osm_match_type
            FROM portals.inmuebles_raw i
            LEFT JOIN portals.detecciones d ON i.id = d.inmueble_id
            WHERE i.is_active = TRUE
              AND i.lat BETWEEN :min_lat AND :max_lat
              AND i.lon BETWEEN :min_lon AND :max_lon
              AND (d.score IS NULL OR d.score >= :min_score)
        """)
        
        min_score = self.config.scoring['detection_threshold']
        
        result = await self.db.execute(
            query,
            {
                'min_lat': min_lat,
                'max_lat': max_lat,
                'min_lon': min_lon,
                'max_lon': max_lon,
                'min_score': min_score
            }
        )
        
        inmuebles = result.fetchall()
        
        # Filtrar por región exacta (no solo bbox)
        alerts = []
        
        for row in inmuebles:
            # Verificar que está dentro de la región (no solo bbox)
            if not region.contains_point(row.lat, row.lon):
                continue
            
            # Calcular distancia al centro
            distance_to_center = self._calculate_distance(
                region.center_lat, region.center_lon,
                row.lat, row.lon
            ) if region.center_lat else None
            
            # Si no tiene score, calcularlo ahora
            if row.score is None:
                score, evidences = await self._score_inmueble(row)
                status = self._get_status_for_score(score)
                
                # Guardar detección si supera umbral
                if score >= min_score:
                    await self._save_detection(row, score, evidences, status)
            else:
                score = row.score
                evidences = row.evidences
                status = row.status
            
            # Buscar iglesias OSM cercanas para la alerta
            osm_church_id = row.osm_match_id
            osm_church_name = None
            osm_distance = None
            
            if row.lat and row.lon:
                churches = self.overpass.find_churches_nearby(
                    row.lat, row.lon, 150
                )
                if churches:
                    closest = churches[0]
                    osm_church_id = closest.osm_id
                    osm_church_name = closest.name
                    osm_distance = closest.distance
            
            # Crear alerta
            alert = RegionAlert(
                region_id=region_id,
                portal=row.portal,
                inmueble_id=row.id_portal,
                titulo=row.titulo,
                precio=float(row.precio) if row.precio else None,
                score=float(score),
                status=status,
                lat=row.lat,
                lon=row.lon,
                distance_to_center_m=distance_to_center,
                osm_church_id=osm_church_id,
                osm_church_name=osm_church_name,
                osm_distance_m=osm_distance,
                detected_at=datetime.now()
            )
            
            alerts.append(alert)
        
        # Guardar alertas en BD
        if alerts:
            await self._save_alerts(alerts)
        
        # Actualizar last_checked de la región
        await self._update_region_last_checked(region_id)
        
        return alerts
    
    async def _score_inmueble(self, inmueble_row) -> Tuple[float, List[str]]:
        """
        Calcula score de un inmueble
        """
        # Construir dict con datos del inmueble
        inmueble_data = {
            'titulo': inmueble_row.titulo or '',
            'descripcion': inmueble_row.descripcion or '',
            'tipo': None,  # TODO: extraer de caracteristicas
            'superficie': None,  # TODO: extraer
            'caracteristicas_basicas': inmueble_row.caracteristicas or [],
            'caracteristicas_extras': [],
            'lat': inmueble_row.lat,
            'lon': inmueble_row.lon,
            'geo_type': inmueble_row.geo_type
        }
        
        # Calcular score
        score, evidences = self.scorer.score(inmueble_data)
        
        return score, evidences
    
    # ========================================================================
    # Monitoreo continuo
    # ========================================================================
    
    async def start_monitoring(
        self,
        region_id: int,
        interval_hours: int = 24
    ):
        """
        Inicia monitoreo continuo de una región
        
        Args:
            region_id: ID de la región
            interval_hours: Intervalo de re-scan en horas
        """
        if region_id in self.active_monitors:
            print(f"Region {region_id} already being monitored")
            return
        
        # Crear tarea de monitoreo
        task = asyncio.create_task(
            self._monitor_loop(region_id, interval_hours)
        )
        
        self.active_monitors[region_id] = task
        
        print(f"✓ Monitoring started for region {region_id} (interval: {interval_hours}h)")
    
    async def stop_monitoring(self, region_id: int):
        """Detiene el monitoreo de una región"""
        if region_id not in self.active_monitors:
            print(f"Region {region_id} is not being monitored")
            return
        
        task = self.active_monitors[region_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.active_monitors[region_id]
        
        print(f"✓ Monitoring stopped for region {region_id}")
    
    async def stop_all_monitoring(self):
        """Detiene todos los monitoreos activos"""
        for region_id in list(self.active_monitors.keys()):
            await self.stop_monitoring(region_id)
    
    async def _monitor_loop(self, region_id: int, interval_hours: int):
        """Loop de monitoreo continuo"""
        while True:
            try:
                # Scan
                alerts = await self.scan_region(region_id)
                
                if alerts:
                    print(f"Region {region_id}: {len(alerts)} new alerts")
                    # TODO: Enviar notificaciones (email, webhook, etc.)
                
                # Esperar intervalo
                await asyncio.sleep(interval_hours * 3600)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error monitoring region {region_id}: {e}")
                await asyncio.sleep(300)  # Esperar 5 min antes de reintentar
    
    # ========================================================================
    # Gestión de regiones
    # ========================================================================
    
    async def list_regions(
        self,
        active_only: bool = True
    ) -> List[GeoRegion]:
        """Lista todas las regiones"""
        query = text("""
            SELECT 
                id, name, shape_type,
                center_lat, center_lon, radius_m,
                address, description,
                is_active, last_checked,
                created_at
            FROM regions.geo_regions
            WHERE (:active_only = FALSE OR is_active = TRUE)
            ORDER BY created_at DESC
        """)
        
        result = await self.db.execute(query, {'active_only': active_only})
        rows = result.fetchall()
        
        regions = []
        for row in rows:
            region = GeoRegion(
                id=row.id,
                name=row.name,
                shape_type=RegionShape(row.shape_type),
                center_lat=row.center_lat,
                center_lon=row.center_lon,
                radius_m=row.radius_m,
                address=row.address,
                description=row.description,
                is_active=row.is_active,
                last_checked=row.last_checked,
                created_at=row.created_at
            )
            regions.append(region)
        
        return regions
    
    async def get_region_alerts(
        self,
        region_id: int,
        limit: int = 50,
        unnotified_only: bool = False
    ) -> List[RegionAlert]:
        """Obtiene alertas de una región"""
        query = text("""
            SELECT 
                id, region_id, portal, inmueble_id,
                titulo, precio, score, status,
                lat, lon, distance_to_center_m,
                osm_church_id, osm_church_name, osm_distance_m,
                detected_at, notified, notified_at
            FROM regions.region_alerts
            WHERE region_id = :region_id
              AND (:unnotified_only = FALSE OR notified = FALSE)
            ORDER BY detected_at DESC
            LIMIT :limit
        """)
        
        result = await self.db.execute(
            query,
            {
                'region_id': region_id,
                'unnotified_only': unnotified_only,
                'limit': limit
            }
        )
        
        rows = result.fetchall()
        
        alerts = []
        for row in rows:
            alert = RegionAlert(
                id=row.id,
                region_id=row.region_id,
                portal=row.portal,
                inmueble_id=row.inmueble_id,
                titulo=row.titulo,
                precio=float(row.precio) if row.precio else None,
                score=float(row.score),
                status=row.status,
                lat=row.lat,
                lon=row.lon,
                distance_to_center_m=row.distance_to_center_m,
                osm_church_id=row.osm_church_id,
                osm_church_name=row.osm_church_name,
                osm_distance_m=row.osm_distance_m,
                detected_at=row.detected_at,
                notified=row.notified,
                notified_at=row.notified_at
            )
            alerts.append(alert)
        
        return alerts
    
    async def mark_alerts_notified(self, alert_ids: List[int]):
        """Marca alertas como notificadas"""
        query = text("""
            UPDATE regions.region_alerts
            SET notified = TRUE,
                notified_at = NOW()
            WHERE id = ANY(:alert_ids)
        """)
        
        await self.db.execute(query, {'alert_ids': alert_ids})
        await self.db.commit()
    
    async def deactivate_region(self, region_id: int):
        """Desactiva una región (deja de monitorearse)"""
        # Detener monitoreo si está activo
        if region_id in self.active_monitors:
            await self.stop_monitoring(region_id)
        
        # Desactivar en BD
        query = text("""
            UPDATE regions.geo_regions
            SET is_active = FALSE
            WHERE id = :region_id
        """)
        
        await self.db.execute(query, {'region_id': region_id})
        await self.db.commit()
    
    async def delete_region(self, region_id: int):
        """Elimina una región y todas sus alertas"""
        # Detener monitoreo
        if region_id in self.active_monitors:
            await self.stop_monitoring(region_id)
        
        # Eliminar (cascade eliminará alertas)
        query = text("""
            DELETE FROM regions.geo_regions
            WHERE id = :region_id
        """)
        
        await self.db.execute(query, {'region_id': region_id})
        await self.db.commit()
    
    # ========================================================================
    # Métodos auxiliares privados
    # ========================================================================
    
    async def _save_region(self, region: GeoRegion) -> GeoRegion:
        """Guarda región en BD"""
        query = text("""
            INSERT INTO regions.geo_regions (
                name, shape_type,
                center_lat, center_lon, radius_m,
                address, description,
                is_active
            ) VALUES (
                :name, :shape_type,
                :center_lat, :center_lon, :radius_m,
                :address, :description,
                TRUE
            )
            RETURNING id, created_at
        """)
        
        result = await self.db.execute(
            query,
            {
                'name': region.name,
                'shape_type': region.shape_type.value,
                'center_lat': region.center_lat,
                'center_lon': region.center_lon,
                'radius_m': region.radius_m,
                'address': region.address,
                'description': region.description
            }
        )
        
        row = result.fetchone()
        region.id = row.id
        region.created_at = row.created_at
        
        await self.db.commit()
        
        return region
    
    async def _get_region(self, region_id: int) -> Optional[GeoRegion]:
        """Obtiene región de BD"""
        query = text("""
            SELECT 
                id, name, shape_type,
                center_lat, center_lon, radius_m,
                address, description,
                is_active, last_checked, created_at
            FROM regions.geo_regions
            WHERE id = :region_id
        """)
        
        result = await self.db.execute(query, {'region_id': region_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return GeoRegion(
            id=row.id,
            name=row.name,
            shape_type=RegionShape(row.shape_type),
            center_lat=row.center_lat,
            center_lon=row.center_lon,
            radius_m=row.radius_m,
            address=row.address,
            description=row.description,
            is_active=row.is_active,
            last_checked=row.last_checked,
            created_at=row.created_at
        )
    
    async def _save_detection(
        self,
        inmueble_row,
        score: float,
        evidences: List[str],
        status: str
    ):
        """Guarda detección en BD"""
        query = text("""
            INSERT INTO portals.detecciones (
                inmueble_id, score, status, evidences,
                precio_inicial, precio_actual
            ) VALUES (
                :inmueble_id, :score, :status, :evidences,
                :precio, :precio
            )
            ON CONFLICT (inmueble_id) DO UPDATE
            SET score = :score,
                status = :status,
                evidences = :evidences,
                last_updated_at = NOW()
        """)
        
        await self.db.execute(
            query,
            {
                'inmueble_id': inmueble_row.id,
                'score': score,
                'status': status,
                'evidences': evidences,
                'precio': float(inmueble_row.precio) if inmueble_row.precio else None
            }
        )
        
        await self.db.commit()
    
    async def _save_alerts(self, alerts: List[RegionAlert]):
        """Guarda múltiples alertas en BD"""
        if not alerts:
            return
        
        # Preparar datos para bulk insert
        values = []
        for alert in alerts:
            values.append({
                'region_id': alert.region_id,
                'portal': alert.portal,
                'inmueble_id': alert.inmueble_id,
                'titulo': alert.titulo,
                'precio': alert.precio,
                'score': alert.score,
                'status': alert.status,
                'lat': alert.lat,
                'lon': alert.lon,
                'distance_to_center_m': alert.distance_to_center_m,
                'osm_church_id': alert.osm_church_id,
                'osm_church_name': alert.osm_church_name,
                'osm_distance_m': alert.osm_distance_m
            })
        
        # Bulk insert (evitar duplicados)
        query = text("""
            INSERT INTO regions.region_alerts (
                region_id, portal, inmueble_id,
                titulo, precio, score, status,
                lat, lon, distance_to_center_m,
                osm_church_id, osm_church_name, osm_distance_m
            ) VALUES (
                :region_id, :portal, :inmueble_id,
                :titulo, :precio, :score, :status,
                :lat, :lon, :distance_to_center_m,
                :osm_church_id, :osm_church_name, :osm_distance_m
            )
            ON CONFLICT (region_id, portal, inmueble_id) DO NOTHING
        """)
        
        await self.db.execute(query, values)
        await self.db.commit()
    
    async def _update_region_last_checked(self, region_id: int):
        """Actualiza timestamp de último check"""
        query = text("""
            UPDATE regions.geo_regions
            SET last_checked = NOW()
            WHERE id = :region_id
        """)
        
        await self.db.execute(query, {'region_id': region_id})
        await self.db.commit()
    
    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calcula distancia en metros usando Haversine"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Radio de la Tierra en metros
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2) ** 2 + \
            cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        
        return distance
    
    def _get_status_for_score(self, score: float) -> str:
        """Determina status según score"""
        statuses = self.config.scoring['statuses']
        threshold = self.config.scoring['detection_threshold']
        
        if score == 100:
            return statuses['confirmed']
        elif score >= threshold:
            return statuses['detected']
        elif score > 0:
            return statuses['monitoring']
        else:
            return 'no_detectado'