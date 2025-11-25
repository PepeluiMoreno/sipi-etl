from alembic import context
from sqlalchemy import engine_from_config, pool
from db.models.base import Base
from config.settings import settings

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(context.get_x_argument(), prefix="sqlalchemy.", poolclass=pool.NullPool, url=settings.DB_CONN_STRING_ORM)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
