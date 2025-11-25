import psycopg2
from sqlalchemy import create_engine
from contextlib import contextmanager

# Importar settings después para evitar circular imports
try:
    from config.settings import settings
except ImportError:
    settings = None

@contextmanager
def get_raw_connection():
    conn = psycopg2.connect(settings.DB_CONN_STRING if settings else "postgresql://sipi:sipi@db:5432/sipi")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

engine = create_engine(settings.DB_CONN_STRING_ORM if settings else "postgresql://sipi:sipi@db:5432/sipi", pool_size=5)
from sqlalchemy.orm import sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
