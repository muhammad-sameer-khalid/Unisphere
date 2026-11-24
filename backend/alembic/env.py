
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database.base import Base
from app.database.connection import engine

# Import all models so Alembic can detect every table.
import app.models


config = context.config

# Configure Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata containing all 27 tables.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""

    url = engine.url.render_as_string(hide_password=False)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the configured database connection."""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

