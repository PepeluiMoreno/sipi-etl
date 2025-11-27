"""
Script de verificación post-instalación
Ejecutar desde Jupyter después de aplicar los cambios

Uso:
    exec(open('/home/jovyan/dev/sipi-etl/verify_install.py').read())
"""

import asyncio
import sys
from pathlib import Path

print("=" * 80)
print("SIPI-ETL: Verificación de Instalación")
print("=" * 80)
print()

# ============================================================================
# 1. Verificar estructura del proyecto
# ============================================================================
print("1️⃣  Verificando estructura del proyecto...")
print("-" * 80)

project_root = Path.cwd()
if (project_root / 'notebooks').exists():
    project_root = project_root.parent

required_paths = [
    'src',
    'src/modules',
    'src/modules/portals',
    'src/modules/portals/idealista',
    'src/core',
]

all_exist = True
for path in required_paths:
    full_path = project_root / path
    exists = full_path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {path}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n❌ ERROR: Faltan directorios del proyecto")
    print(f"   Verificar que estás en el directorio correcto: {project_root}")
    sys.exit(1)

print(f"\n✓ Estructura del proyecto correcta en: {project_root}")
print()

# Agregar al path si no está
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ============================================================================
# 2. Verificar registry de scrapers
# ============================================================================
print("2️⃣  Verificando registry de scrapers...")
print("-" * 80)

try:
    from src.modules.portals.factory import _SCRAPER_REGISTRY, get_available_portals
    from src.core.etl_event_system import PortalType
    
    portals = get_available_portals()
    portal_names = [p.value for p in portals]
    
    print(f"  Scrapers registrados: {portal_names}")
    
    if PortalType.IDEALISTA in _SCRAPER_REGISTRY:
        print("  ✓ Scraper Idealista encontrado")
    else:
        print("  ✗ Scraper Idealista NO registrado")
        print("\n❌ ERROR: Registry vacío o scraper no registrado")
        print("   Solución: Verificar que __init__.py importa el scraper")
        sys.exit(1)
    
    print("\n✓ Registry configurado correctamente")
    print()
    
except ImportError as e:
    print(f"  ✗ Error importando módulos: {e}")
    print("\n❌ ERROR: No se pueden importar los módulos del proyecto")
    print("   Solución: Verificar la estructura del proyecto y los imports")
    sys.exit(1)

# ============================================================================
# 3. Verificar conexión PostgreSQL
# ============================================================================
print("3️⃣  Verificando conexión PostgreSQL...")
print("-" * 80)

async def test_postgres():
    try:
        from src.modules.portals.base_loader import PostgresConnectionPool
        import os
        
        # Mostrar configuración
        host = os.getenv('POSTGRES_HOST', 'postgis')
        port = os.getenv('POSTGRES_PORT', '5432')
        user = os.getenv('POSTGRES_USER', 'user')
        db = os.getenv('POSTGRES_DB', 'spatialdb')
        
        print(f"  Configuración:")
        print(f"    Host: {host}")
        print(f"    Puerto: {port}")
        print(f"    Usuario: {user}")
        print(f"    Base de datos: {db}")
        print()
        
        # Intentar conexión
        print("  Intentando conectar...")
        pool = await PostgresConnectionPool.get_pool()
        
        async with pool.acquire() as conn:
            version = await conn.fetchval('SELECT version()')
            pg_version = version.split(',')[0]
            print(f"  ✓ Conectado a: {pg_version}")
            
            # Verificar esquema portals
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'portals')"
            )
            
            if schema_exists:
                print("  ✓ Esquema 'portals' existe")
                
                # Verificar tablas principales
                tables_to_check = ['inmuebles_raw', 'detecciones', 'cambios', 'duplicates']
                
                for table_name in tables_to_check:
                    table_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'portals' AND table_name = $1)", table_name
                    )
                    
                    if table_exists:
                        count = await conn.fetchval(f"SELECT COUNT(*) FROM portals.{table_name}")
                        print(f"  ✓ Tabla 'portals.{table_name}' existe ({count} registros)")
                    else:
                        print(f"  ⚠ Tabla 'portals.{table_name}' no existe")
                        print(f"    Ejecuta: init_db_real.py")
            else:
                print("  ⚠ Esquema 'portals' no existe")
                print("    (Ejecuta init_db_real.py para crear el esquema)")
        
        await PostgresConnectionPool.close_pool()
        print("\n✓ PostgreSQL funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR conectando a PostgreSQL: {e}")
        print("\nPosibles causas:")
        print("  1. El contenedor 'postgis' no está corriendo")
        print("  2. Las credenciales son incorrectas")
        print("  3. El host debería ser 'postgis' (no 'localhost')")
        print("\nVerificar con: docker ps | grep postgis")
        return False

postgres_ok = asyncio.run(test_postgres())
print()

if not postgres_ok:
    sys.exit(1)

# ============================================================================
# 4. Verificar Redis (opcional)
# ============================================================================
print("4️⃣  Verificando conexión Redis...")
print("-" * 80)

async def test_redis():
    try:
        from src.modules.portals.redis_cache import RedisCache
        import os
        
        # Mostrar configuración
        host = os.getenv('REDIS_HOST', 'redis')
        port = os.getenv('REDIS_PORT', '6379')
        
        print(f"  Configuración:")
        print(f"    Host: {host}")
        print(f"    Puerto: {port}")
        print()
        
        # Intentar conexión
        print("  Intentando conectar...")
        cache = RedisCache()
        await cache.connect()
        
        # Test básico
        test_key = 'test_verify_install'
        is_dup_1 = await cache.check_duplicate('test', test_key, ttl_hours=1)
        is_dup_2 = await cache.check_duplicate('test', test_key, ttl_hours=1)
        
        await cache.close()
        
        if not is_dup_1 and is_dup_2:
            print("  ✓ Redis funcionando correctamente")
            print("  ✓ Deduplicación funcional")
            print("\n✓ Redis disponible")
            return True
        else:
            print("  ⚠ Redis conecta pero la deduplicación no funciona como esperado")
            return False
        
    except Exception as e:
        print(f"  ⚠ Redis no disponible: {e}")
        print("  (Opcional - el sistema puede funcionar sin Redis)")
        print("  La deduplicación estará deshabilitada")
        return False

redis_ok = asyncio.run(test_redis())
print()

# ============================================================================
# 5. Test de scraper
# ============================================================================
print("5️⃣  Verificando scraper de Idealista...")
print("-" * 80)

try:
    from src.modules.portals.factory import create_scraper
    from src.core.etl_event_system import PortalType
    
    print("  Creando instancia del scraper...")
    scraper = create_scraper(PortalType.IDEALISTA)
    
    print(f"  ✓ Scraper creado: {scraper.__class__.__name__}")
    print(f"  ✓ Portal: {scraper.portal_type.value}")
    print(f"  ✓ Base URL: {scraper.base_url}")
    
    # Test de método get_search_url
    test_url = scraper.get_search_url(provincia='sevilla', pagina=1)
    print(f"  ✓ URL de prueba generada: {test_url}")
    
    print("\n✓ Scraper funcionando correctamente")
    
except Exception as e:
    print(f"\n❌ ERROR creando scraper: {e}")
    sys.exit(1)

print()

# ============================================================================
# Resumen final
# ============================================================================
print("=" * 80)
print("📊 RESUMEN DE VERIFICACIÓN")
print("=" * 80)
print()
print("✓ Estructura del proyecto")
print("✓ Registry de scrapers")
print("✓ Conexión PostgreSQL" if postgres_ok else "✗ Conexión PostgreSQL")
print("✓ Conexión Redis" if redis_ok else "⚠ Redis no disponible (opcional)")
print("✓ Scraper Idealista")
print()

if postgres_ok:
    print("🎉 ¡Todo listo! Puedes usar el notebook test_pipeline_fixed.ipynb")
    print()
    print("Próximos pasos:")
    print("  1. Abrir test_pipeline_fixed.ipynb")
    print("  2. Ejecutar las celdas en orden")
    print("  3. Verificar que no hay errores")
    print()
else:
    print("⚠ Hay problemas que resolver antes de continuar")
    print("   Revisa los errores arriba y aplica las soluciones sugeridas")
    print()

print("=" * 80)