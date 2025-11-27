"""
Ejemplos de uso del Region Monitor
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.geo.region_monitor import RegionMonitor


async def example_create_regions():
    """Crear regiones de monitoreo"""
    
    # Setup DB
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/sipi")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        monitor = RegionMonitor(session)
        
        # 1. Región alrededor de la Catedral de Sevilla
        print("Creando región: Catedral de Sevilla...")
        region1 = await monitor.create_region_from_address(
            address="Catedral de Sevilla",
            radius_m=500,
            name="Monitoreo Catedral Sevilla",
            auto_start=True
        )
        
        print(f"✓ Región creada: {region1.name} (ID: {region1.id})")
        
        # 2. Región alrededor de iglesia específica
        print("\nCreando región: Basílica de la Macarena...")
        region2 = await monitor.create_region_from_church(
            church_name="Basílica de la Macarena",
            radius_m=300,
            auto_start=True
        )
        
        print(f"✓ Región creada: {region2.name} (ID: {region2.id})")
        
        # 3. Región con polígono personalizado (Casco Antiguo de Sevilla)
        print("\nCreando región: Casco Antiguo Sevilla...")
        casco_antiguo_coords = [
            (37.3920, -5.9945),  # NW
            (37.3920, -5.9850),  # NE
            (37.3850, -5.9850),  # SE
            (37.3850, -5.9945),  # SW
        ]
        
        region3 = await monitor.create_region_from_polygon(
            coordinates=casco_antiguo_coords,
            name="Casco Antiguo Sevilla",
            description="Monitoreo del centro histórico",
            auto_start=True
        )
        
        print(f"✓ Región creada: {region3.name} (ID: {region3.id})")
        
        # Ver alertas generadas
        print("\n" + "="*60)
        print("ALERTAS GENERADAS")
        print("="*60)
        
        for region in [region1, region2, region3]:
            alerts = await monitor.get_region_alerts(region.id)
            print(f"\n{region.name}:")
            print(f"  {len(alerts)} alertas")
            
            for alert in alerts[:3]:  # Mostrar primeras 3
                print(f"  - {alert.titulo[:50]}...")
                print(f"    Precio: {alert.precio}€, Score: {alert.score}")
                if alert.osm_church_name:
                    print(f"    Iglesia cercana: {alert.osm_church_name} ({alert.osm_distance_m:.0f}m)")


async def example_monitoring_loop():
    """Monitoreo continuo"""
    
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/sipi")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        monitor = RegionMonitor(session)
        
        # Iniciar monitoreo de región existente
        region_id = 1
        await monitor.start_monitoring(region_id, interval_hours=24)
        
        print(f"Monitoreo iniciado para región {region_id}")
        print("Presiona Ctrl+C para detener...")
        
        try:
            # Mantener el programa corriendo
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await monitor.stop_monitoring(region_id)
            print("\nMonitoreo detenido")


if __name__ == '__main__':
    print("=== Ejemplo 1: Crear Regiones ===")
    asyncio.run(example_create_regions())
    
    # print("\n=== Ejemplo 2: Monitoreo Continuo ===")
    # asyncio.run(example_monitoring_loop())