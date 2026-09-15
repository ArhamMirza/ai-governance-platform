from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (ensures all models register on Base.metadata)
from alembic import context
from app.core import vector_store
from app.core.config import get_settings
from app.core.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Document search's FTS5 and sqlite-vec tables are virtual tables created by
# raw DDL, so they aren't in the models -- and SQLite backs each one with
# several shadow tables. Left visible to autogenerate, every future revision
# would propose dropping the search index.
_SEARCH_TABLE_PREFIXES = ("document_chunks_fts", "chunk_vectors")


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001
    table = name if type_ == "table" else getattr(getattr(obj, "table", None), "name", "")
    return not str(table or "").startswith(_SEARCH_TABLE_PREFIXES)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata, include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # A migration that creates the vec0 table needs the extension loaded on
    # its own connection, the same as the app's.
    vector_store.register(connectable)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
