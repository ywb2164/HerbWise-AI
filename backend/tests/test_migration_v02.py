import importlib

import app.models  # noqa: F401
from app.core.database import Base


def test_v02_migration_creates_and_drops_every_new_table(monkeypatch) -> None:
    migration = importlib.import_module(
        "migrations.versions.53e14d9e3d7c_add_auth_and_business_modules"
    )
    created: list[str] = []
    dropped: list[str] = []

    monkeypatch.setattr(migration.op, "add_column", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda name, *_args, **_kwargs: created.append(name),
    )
    monkeypatch.setattr(migration.op, "create_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration.op, "create_unique_constraint", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(migration.op, "drop_constraint", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(migration.op, "drop_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration.op, "drop_table", lambda name, **_kwargs: dropped.append(name)
    )
    monkeypatch.setattr(migration.op, "drop_column", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration, "_table_names", lambda: set(migration._INITIAL_TABLES)
    )
    monkeypatch.setattr(migration, "_column_names", lambda _table: set())
    monkeypatch.setattr(migration, "_unique_names", lambda _table: set())

    migration.upgrade()
    monkeypatch.setattr(migration, "_table_names", lambda: set(Base.metadata.tables))
    monkeypatch.setattr(
        migration,
        "_column_names",
        lambda table: set(Base.metadata.tables[table].columns.keys()),
    )
    monkeypatch.setattr(
        migration,
        "_unique_names",
        lambda _table: {"uq_learner_dimension_code"},
    )
    migration.downgrade()

    expected = set(Base.metadata.tables) - set(migration._INITIAL_TABLES)
    assert set(created) == expected
    assert set(dropped) == expected
    assert dropped == list(reversed(created))


def test_v02_migration_extends_existing_learner_tables(monkeypatch) -> None:
    migration = importlib.import_module(
        "migrations.versions.53e14d9e3d7c_add_auth_and_business_modules"
    )
    added: list[tuple[str, str]] = []

    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: added.append((table, column.name)),
    )
    monkeypatch.setattr(migration.op, "create_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(migration.op, "create_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration.op, "create_unique_constraint", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration, "_table_names", lambda: set(migration._INITIAL_TABLES)
    )
    monkeypatch.setattr(migration, "_column_names", lambda _table: set())
    monkeypatch.setattr(migration, "_unique_names", lambda _table: set())

    migration.upgrade()

    assert ("learner_profiles", "identity_type") in added
    assert ("learner_profiles", "diagnosis_summary") in added
    assert ("learner_dimensions", "dimension_code") in added
    assert ("learner_dimensions", "evidence_json") in added
