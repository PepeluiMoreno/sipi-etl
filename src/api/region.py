"""
API endpoints para gestión de regiones geográficas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from ..db.connection import get_db
from ..core.geo.region_monitor import RegionMonitor
from ..core.geo.models import RegionShape


router = APIRouter(prefix="/api/regions", tags=["regions"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateRegionRequest(BaseModel):
    """Request para crear región"""
    type: str  # 'address', 'church', 'polygon'
    
    # Para type='address'
    address: Optional[str] = None
    radius_m: Optional[int] = 500
    
    # Para type='church'
    church_name: Optional[str] = None
    
    # Para type='polygon'
    coordinates: Optional[List[tuple[float, float]]] = None
    
    # Común
    name: Optional[str] = None
    description: Optional[str] = None
    auto_start: bool = True


class RegionResponse(BaseModel):
    """Response de región"""
    id: int
    name: str
    shape_type: str
    center_lat: Optional[float]
    center_lon: Optional[float]
    radius_m: Optional[int]
    address: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: str
    last_checked: Optional[str]


class AlertResponse(BaseModel):
    """Response de alerta"""
    id: int
    region_id: int
    portal: str
    inmueble_id: str
    titulo: str
    precio: Optional[float]
    score: float
    status: str
    lat: float
    lon: float
    distance_to_center_m: Optional[float]
    osm_church_name: Optional[str]
    osm_distance_m: Optional[float]
    detected_at: str
    notified: bool


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/create", response_model=RegionResponse)
async def create_region(
    request: CreateRegionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una nueva región de monitoreo
    """
    monitor = RegionMonitor(db)
    
    try:
        if request.type == 'address':
            if not request.address:
                raise HTTPException(400, "address is required for type='address'")
            
            region = await monitor.create_region_from_address(
                address=request.address,
                radius_m=request.radius_m or 500,
                name=request.name,
                auto_start=request.auto_start
            )
        
        elif request.type == 'church':
            if not request.church_name:
                raise HTTPException(400, "church_name is required for type='church'")
            
            region = await monitor.create_region_from_church(
                church_name=request.church_name,
                radius_m=request.radius_m or 500,
                auto_start=request.auto_start
            )
        
        elif request.type == 'polygon':
            if not request.coordinates or len(request.coordinates) < 3:
                raise HTTPException(400, "coordinates with at least 3 points required for type='polygon'")
            
            if not request.name:
                raise HTTPException(400, "name is required for type='polygon'")
            
            region = await monitor.create_region_from_polygon(
                coordinates=request.coordinates,
                name=request.name,
                description=request.description,
                auto_start=request.auto_start
            )
        
        else:
            raise HTTPException(400, f"Invalid type: {request.type}")
        
        if not region:
            raise HTTPException(500, "Failed to create region")
        
        return RegionResponse(
            id=region.id,
            name=region.name,
            shape_type=region.shape_type.value,
            center_lat=region.center_lat,
            center_lon=region.center_lon,
            radius_m=region.radius_m,
            address=region.address,
            description=region.description,
            is_active=region.is_active,
            created_at=region.created_at.isoformat() if region.created_at else None,
            last_checked=region.last_checked.isoformat() if region.last_checked else None
        )
    
    except Exception as e:
        raise HTTPException(500, f"Error creating region: {str(e)}")


@router.get("/", response_model=List[RegionResponse])
async def list_regions(
    only_active: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las regiones"""
    monitor = RegionMonitor(db)
    regions = await monitor.get_all_regions(only_active=only_active)
    
    return [
        RegionResponse(
            id=r.id,
            name=r.name,
            shape_type=r.shape_type.value,
            center_lat=r.center_lat,
            center_lon=r.center_lon,
            radius_m=r.radius_m,
            address=r.address,
            description=r.description,
            is_active=r.is_active,
            created_at=r.created_at.isoformat() if r.created_at else None,
            last_checked=r.last_checked.isoformat() if r.last_checked else None
        )
        for r in regions
    ]


@router.post("/{region_id}/scan")
async def scan_region(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Escanea manualmente una región"""
    monitor = RegionMonitor(db)
    alerts = await monitor.scan_region(region_id)
    
    return {
        "region_id": region_id,
        "alerts_generated": len(alerts),
        "message": f"Scan completed. {len(alerts)} new alerts."
    }


@router.get("/{region_id}/alerts", response_model=List[AlertResponse])
async def get_region_alerts(
    region_id: int,
    only_unnotified: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene alertas de una región"""
    monitor = RegionMonitor(db)
    alerts = await monitor.get_region_alerts(region_id, only_unnotified)
    
    return [
        AlertResponse(
            id=a.id,
            region_id=a.region_id,
            portal=a.portal,
            inmueble_id=a.inmueble_id,
            titulo=a.titulo,
            precio=a.precio,
            score=a.score,
            status=a.status,
            lat=a.lat,
            lon=a.lon,
            distance_to_center_m=a.distance_to_center_m,
            osm_church_name=a.osm_church_name,
            osm_distance_m=a.osm_distance_m,
            detected_at=a.detected_at.isoformat(),
            notified=a.notified
        )
        for a in alerts
    ]


@router.post("/{region_id}/start-monitoring")
async def start_monitoring(
    region_id: int,
    interval_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Inicia monitoreo continuo de una región"""
    monitor = RegionMonitor(db)
    await monitor.start_monitoring(region_id, interval_hours)
    
    return {
        "region_id": region_id,
        "interval_hours": interval_hours,
        "message": f"Monitoring started (every {interval_hours}h)"
    }


@router.post("/{region_id}/stop-monitoring")
async def stop_monitoring(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Detiene monitoreo de una región"""
    monitor = RegionMonitor(db)
    await monitor.stop_monitoring(region_id)
    
    return {
        "region_id": region_id,
        "message": "Monitoring stopped"
    }


@router.delete("/{region_id}")
async def delete_region(
    region_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina una región"""
    monitor = RegionMonitor(db)
    await monitor.delete_region(region_id)
    
    return {
        "region_id": region_id,
        "message": "Region deleted"
    }