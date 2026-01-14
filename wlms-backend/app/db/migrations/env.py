import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Column, MetaData, String, Table, engine_from_config, inspect, pool, text

from app.models.base import Base

# Import models here so Alembic can discover metadata in Base.metadata
# (Add more imports as we add models)
from app.models import client  # noqa: F401
from app.models import discrepancy  # noqa: F401
from app.models import inbound  # noqa: F401
from app.models import inventory  # noqa: F401
from app.models import inventory_reservation  # noqa: F401
from app.models import billing  # noqa: F401
from app.models import audit  # noqa: F401
from app.models import auth_tokens  # noqa: F401
from app.models import file  # noqa: F401
from app.models import notification  # noqa: F401
from app.models import location  # noqa: F401
from app.models import product  # noqa: F401
from app.models import product_batch  # noqa: F401
from app.models import outbound  # noqa: F401
from app.models import picking  # noqa: F401
from app.models import return_  # noqa: F401
from app.models import tenant  # noqa: F401
from app.models import user  # noqa: F401
from app.models import warehouse  # noqa: F401
from app.models import warehouse_zone  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    # Prefer environment; fall back to alembic.ini interpolation.
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


target_metadata = Base.metadata


def _ensure_alembic_version_column_length(connection) -> None:
    """
    Alembic's default version table uses VARCHAR(32). Our revision ids are longer
    (e.g. '0010_auth_invites_reset_email_outbox'), so on a fresh DB the migration
    run can fail when alembic tries to UPDATE the version.

    Fix: ensure the version table exists with a larger column (or alter it if it exists).
    """
    insp = inspect(connection)
    if "alembic_version" not in insp.get_table_names():
        Table(
            "alembic_version",
            MetaData(),
            Column("version_num", String(255), primary_key=True),
        ).create(connection)
        return

    # If it exists already (likely VARCHAR(32)), widen it.
    # Postgres supports this; if other dialects are used, we ignore failures.
    try:
        connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"))
    except Exception:
        pass


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.begin() as connection:
        _ensure_alembic_version_column_length(connection)
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()




