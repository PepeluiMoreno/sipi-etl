"""
Sistema centralizado de eventos para monitoreo ETL
Todos los portales inmobiliarios emiten eventos a través de este sistema
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from fastapi import WebSocket


class EventType(Enum):
    """Tipos de eventos ETL"""
    # Scraping
    SCRAPING_STARTED = "scraping_started"
    SCRAPING_PROGRESS = "scraping_progress"
    SCRAPING_COMPLETED = "scraping_completed"
    SCRAPING_ERROR = "scraping_error"
    SCRAPING_PAUSED = "scraping_paused"
    
    # Detección
    DETECTION_FOUND = "detection_found"
    DETECTION_CONFIRMED = "detection_confirmed"
    
    # Matching
    MATCH_FOUND = "match_found"
    MATCH_VALIDATED = "match_validated"
    
    # Sistema
    PORTAL_STATUS_CHANGE = "portal_status_change"
    CONFIG_UPDATED = "config_updated"


class PortalType(Enum):
    """Portales inmobiliarios soportados"""
    IDEALISTA = "idealista"
    FOTOCASA = "fotocasa"
    PISOS_COM = "pisos_com"
    HABITACLIA = "habitaclia"
    # Añadir más portales aquí


@dataclass
class ETLEvent:
    """Evento del sistema ETL"""
    event_type: EventType
    portal: PortalType
    timestamp: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return {
            "event_type": self.event_type.value,
            "portal": self.portal.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata or {}
        }


class ETLEventBus:
    """
    Bus central de eventos ETL
    Singleton que coordina todos los eventos de todos los portales
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.websocket_connections: List[WebSocket] = []
        self.event_history: List[ETLEvent] = []
        self.max_history = 1000
        self.subscribers: Dict[EventType, List[Callable]] = {}
        
        # Estado actual de cada portal
        self.portal_states: Dict[PortalType, Dict[str, Any]] = {}
    
    async def emit(self, event: ETLEvent):
        """
        Emite un evento a todos los subscribers y WebSockets
        """
        # Guardar en historial
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Actualizar estado del portal
        await self._update_portal_state(event)
        
        # Notificar subscribers (callbacks síncronos)
        await self._notify_subscribers(event)
        
        # Broadcast a WebSockets
        await self._broadcast_to_websockets(event)
    
    async def _update_portal_state(self, event: ETLEvent):
        """Actualiza el estado interno del portal basado en el evento"""
        portal = event.portal
        
        if portal not in self.portal_states:
            self.portal_states[portal] = {
                "status": "idle",
                "current_task": None,
                "progress": 0,
                "total_scraped": 0,
                "total_detected": 0,
                "last_activity": None,
                "errors": []
            }
        
        state = self.portal_states[portal]
        state["last_activity"] = event.timestamp
        
        # Actualizar según tipo de evento
        if event.event_type == EventType.SCRAPING_STARTED:
            state["status"] = "running"
            state["current_task"] = event.data.get("task_name")
            state["progress"] = 0
            
        elif event.event_type == EventType.SCRAPING_PROGRESS:
            state["progress"] = event.data.get("progress", 0)
            state["current_task"] = event.data.get("current_item")
            
        elif event.event_type == EventType.SCRAPING_COMPLETED:
            state["status"] = "idle"
            state["current_task"] = None
            state["progress"] = 100
            state["total_scraped"] = event.data.get("total_scraped", 0)
            
        elif event.event_type == EventType.SCRAPING_ERROR:
            state["status"] = "error"
            state["errors"].append({
                "timestamp": event.timestamp,
                "error": event.data.get("error")
            })
            # Mantener solo últimos 10 errores
            if len(state["errors"]) > 10:
                state["errors"].pop(0)
        
        elif event.event_type == EventType.DETECTION_FOUND:
            state["total_detected"] += 1
    
    async def _notify_subscribers(self, event: ETLEvent):
        """Notifica a callbacks registrados"""
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Error in subscriber callback: {e}")
    
    async def _broadcast_to_websockets(self, event: ETLEvent):
        """Envía evento a todos los WebSockets conectados"""
        if not self.websocket_connections:
            return
        
        message = event.to_dict()
        
        # Enviar a todos los clientes conectados
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        # Limpiar conexiones cerradas
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Registra un callback para un tipo de evento"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Desregistra un callback"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
    
    async def add_websocket(self, websocket: WebSocket):
        """Registra una nueva conexión WebSocket"""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        # Enviar estado actual de todos los portales
        await websocket.send_json({
            "type": "initial_state",
            "portals": {
                portal.value: state 
                for portal, state in self.portal_states.items()
            }
        })
    
    def remove_websocket(self, websocket: WebSocket):
        """Elimina una conexión WebSocket"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
    
    def get_portal_state(self, portal: PortalType) -> Dict[str, Any]:
        """Obtiene el estado actual de un portal"""
        return self.portal_states.get(portal, {
            "status": "idle",
            "current_task": None,
            "progress": 0,
            "total_scraped": 0,
            "total_detected": 0,
            "last_activity": None,
            "errors": []
        })
    
    def get_all_portal_states(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todos los portales"""
        return {
            portal.value: self.get_portal_state(portal)
            for portal in PortalType
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene eventos recientes"""
        return [event.to_dict() for event in self.event_history[-limit:]]


# Singleton global
event_bus = ETLEventBus()