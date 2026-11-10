import os
from logging.config import fileConfig
import sys
from pathlib import Path
from dotenv import load_dotenv
from alembic import context
from sqlalchemy import engine_from_config, pool

# 0. Load .env FIRST so os.environ can find DATABASE_URL
# If your .env file is inside the backend folder, change this to: alembic_dir.parent / "backend" / ".env"
env_path = alembic_dir = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 1. Modify sys.path before attempting any app-level imports
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# 2. Now safe to import your application models and base metadata
import app.models  # noqa: F401  (registers models on Base.metadata)
from app.models.base import Base

config = context.config

# Safely get DATABASE_URL with a fallback if needed
database_url = os.getenv("DATABASE_URL", "sqlite:///./backend/mockwright.db")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()