import asyncio
from logging.config import fileConfig

from alembic import context
from app.admin import models as admin_models  # noqa: F401
from app.config import Settings
from app.identity.models import Base
from app.profiles import models as profile_models  # noqa: F401
from app.readings import models as reading_models  # noqa: F401
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=Settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def configure_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = Settings().database_url
    engine = async_engine_from_config(section, prefix="sqlalchemy.", pool_pre_ping=True)
    async with engine.connect() as connection:
        await connection.run_sync(configure_connection)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
