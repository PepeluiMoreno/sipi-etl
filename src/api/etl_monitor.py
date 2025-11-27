"""
API unificada para monitoreo de ETL de todos los portales
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

from ..core.etl_event_system import event_bus, PortalType

router = APIRouter(prefix="/api/etl", tags=["etl-monitor"])


@router.websocket("/ws")
async def websocket_etl_monitor(websocket: WebSocket):
    """
    WebSocket único para monitorear TODOS los portales en tiempo real
    """
    await event_bus.add_websocket(websocket)
    
    try:
        while True:
            # Mantener conexión abierta
            # Los eventos se envían automáticamente vía event_bus
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        event_bus.remove_websocket(websocket)


@router.get("/portals/status")
async def get_all_portals_status():
    """
    Obtiene el estado actual de TODOS los portales
    """
    return {
        "portals": event_bus.get_all_portal_states(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/portals/{portal}/status")
async def get_portal_status(portal: str):
    """
    Obtiene el estado de un portal específico
    """
    try:
        portal_type = PortalType(portal)
        return {
            "portal": portal,
            "state": event_bus.get_portal_state(portal_type)
        }
    except ValueError:
        raise HTTPException(404, f"Portal '{portal}' no encontrado")


@router.get("/events/recent")
async def get_recent_events(limit: int = 100):
    """
    Obtiene eventos recientes de todos los portales
    """
    return {
        "events": event_bus.get_recent_events(limit),
        "total": len(event_bus.event_history)
    }


@router.get("/stats/global")
async def get_global_stats():
    """
    Estadísticas globales de todos los portales
    """
    states = event_bus.get_all_portal_states()
    
    return {
        "total_scraped": sum(s.get("total_scraped", 0) for s in states.values()),
        "total_detected": sum(s.get("total_detected", 0) for s in states.values()),
        "active_portals": sum(1 for s in states.values() if s.get("status") == "running"),
        "portals": states
    }