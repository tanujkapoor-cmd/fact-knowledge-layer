"""Tiny additive SQLite migrations for the prototype's evolving schema."""

from sqlalchemy import Engine, inspect, text

_ADDITIVE_COLUMNS = {
    "documents": {
        "processed_page_count": "INTEGER NOT NULL DEFAULT 0",
        "extraction_batch_count": "INTEGER NOT NULL DEFAULT 0",
        "provider_attempt_count": "INTEGER NOT NULL DEFAULT 0",
        "retry_count": "INTEGER NOT NULL DEFAULT 0",
        "last_checkpoint_at": "DATETIME",
        "checkpoint_model": "VARCHAR(128)",
        "checkpoint_prompt_version": "VARCHAR(64)",
    },
    "facts": {
        "scope": "TEXT",
        "data_vintage": "TEXT",
        "classification_exclusion_reason": "TEXT",
    },
}


def apply_additive_migrations(engine: Engine) -> None:
    """Add nullable/defaulted columns missing from an existing SQLite database."""

    if engine.dialect.name != "sqlite":
        return
    schema = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in _ADDITIVE_COLUMNS.items():
            if not schema.has_table(table_name):
                continue
            existing = {column["name"] for column in schema.get_columns(table_name)}
            for column_name, declaration in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {declaration}')
                    )
