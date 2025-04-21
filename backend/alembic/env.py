from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel
from pathlib import Path
import os

config = context.config

# Pass DATABASE_URL from env → alembic.ini
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

from app.main import Flashcard  # noqa: E402, F401

target_metadata = SQLModel.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
