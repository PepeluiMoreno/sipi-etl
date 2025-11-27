"""
Orquestador de pipelines usando el sistema de eventos
"""
import asyncio
from src.core.etl_event_system import ETLEventBus, PortalType, ETLPhase
from src.modules.portals.factory import create_scraper
from src.modules.portals.loader_factory import create_loader
from src.modules.portals.base_loader import PostgresConnectionPool


class PipelineRunner:
    """
    Ejecuta pipelines ETL con sistema de eventos
    """
    
    def __init__(self, event_bus: ETLEventBus):
        self.event_bus = event_bus
    
    async def run_pipeline(
        self,
        portal: PortalType,
        provincia: str,
        max_pages: int = 5
    ):
        """
        Ejecuta pipeline completo con eventos
        """
        # Emit start
        await self.event_bus.emit_phase_start(portal, ETLPhase.EXTRACT)
        
        db_pool = await PostgresConnectionPool.get_pool()
        
        scraper = create_scraper(portal)
        loader = await create_loader(portal, db_pool)
        loader.driver = scraper.driver
        
        try:
            async for inmueble in scraper.scrape_provincia(provincia, max_pages):
                await loader.load(inmueble)
            
            await self.event_bus.emit_phase_complete(portal, ETLPhase.LOAD)
            
        except Exception as e:
            await self.event_bus.emit_error(portal, ETLPhase.LOAD, str(e))
            raise
        
        finally:
            await loader.close()
            await PostgresConnectionPool.close_pool()


# Uso
async def main():
    event_bus = ETLEventBus()
    runner = PipelineRunner(event_bus)
    
    await runner.run_pipeline(
        PortalType.IDEALISTA,
        provincia="sevilla",
        max_pages=3
    )

if __name__ == '__main__':
    asyncio.run(main())