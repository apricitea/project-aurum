"""Unit tests for DatabaseManager correctness."""
import inspect
import re
import pytest
from unittest.mock import MagicMock


def test_create_alert_sql_uses_correct_column_name():
    """
    Raw SQL in create_alert() must use 'meta_data', matching the DB column.
    The SQLAlchemy model defines Alert.meta_data — not metadata.
    """
    from src.api.database import DatabaseManager

    source = inspect.getsource(DatabaseManager.create_alert)
    insert_match = re.search(
        r"INSERT INTO alerts\s*\(([^)]+)\)", source, re.DOTALL
    )
    assert insert_match, "Could not find INSERT INTO alerts in create_alert()"
    column_list = insert_match.group(1)
    assert "meta_data" in column_list, (
        f"Column list must contain 'meta_data': {column_list}"
    )
    # Ensure the bare 'metadata' (without underscore) is not in the column list
    col_names = [c.strip() for c in column_list.split(",")]
    assert "metadata" not in col_names, (
        f"Column list must not contain 'metadata' (wrong name): {col_names}"
    )


def test_alert_model_column_name():
    """SQLAlchemy Alert model must define column as 'meta_data'."""
    from src.api.database import Alert
    col_names = [c.key for c in Alert.__table__.columns]
    assert "meta_data" in col_names, f"Alert model columns: {col_names}"
    assert "metadata" not in col_names


def test_database_manager_singleton_not_initialized_raises():
    """get_db_manager() must raise RuntimeError before initialization."""
    import src.api.database as db_module
    original = db_module._db_manager_instance
    db_module._db_manager_instance = None
    try:
        with pytest.raises(RuntimeError, match="not initialized"):
            db_module.get_db_manager()
    finally:
        db_module._db_manager_instance = original


def test_set_db_manager_registers_singleton():
    """set_db_manager() must make get_db_manager() return the same instance."""
    import src.api.database as db_module
    original = db_module._db_manager_instance
    fake = object()
    db_module.set_db_manager(fake)
    try:
        assert db_module.get_db_manager() is fake
    finally:
        db_module._db_manager_instance = original


def test_guid_type_processes_none():
    """GUID type must return None for None input."""
    from src.api.database import GUID
    guid = GUID()
    dialect = MagicMock()
    dialect.name = "postgresql"
    result = guid.process_bind_param(None, dialect)
    assert result is None


def test_jsonb_type_uses_postgres_jsonb_for_pg_dialect():
    """JSONB custom type must delegate to PostgreSQL JSONB for pg dialect."""
    from src.api.database import JSONB
    from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
    jsonb = JSONB()
    dialect = MagicMock()
    dialect.name = "postgresql"
    descriptor = MagicMock()
    dialect.type_descriptor = MagicMock(return_value=descriptor)
    jsonb.load_dialect_impl(dialect)
    call_arg = dialect.type_descriptor.call_args[0][0]
    assert isinstance(call_arg, PG_JSONB)
