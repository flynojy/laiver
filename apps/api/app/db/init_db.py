from sqlalchemy import inspect, text

from app.db.base import target_metadata
from app.db.session import engine


def _ensure_sqlite_columns() -> None:
    if engine.dialect.name != "sqlite":
        return

    column_fixes = {
        "memories": {
            "confidence_score": "FLOAT NOT NULL DEFAULT 0.5",
        },
        "personas": {
            "confidence_scores": "JSON",
            "evidence_samples": "JSON",
        },
        "skills": {
            "version": "VARCHAR(40) NOT NULL DEFAULT '1.0.0'",
            "title": "VARCHAR(160) NOT NULL DEFAULT ''",
        },
        "skill_invocations": {
            "started_at": "DATETIME",
            "finished_at": "DATETIME",
        },
        "connector_deliveries": {
            "conversation_mapping_id": "VARCHAR(36)",
            "internal_conversation_id": "VARCHAR(36)",
            "debug_payload": "JSON",
        },
        "fine_tune_jobs": {
            "registered_provider_id": "VARCHAR(36)",
        },
    }

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in column_fixes.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
            if table_name == "personas":
                connection.execute(
                    text(
                        "UPDATE personas SET confidence_scores='{}' "
                        "WHERE confidence_scores IS NULL OR confidence_scores = ''"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE personas SET evidence_samples='{}' "
                        "WHERE evidence_samples IS NULL OR evidence_samples = ''"
                    )
                )
            if table_name == "skills":
                connection.execute(
                    text("UPDATE skills SET version='1.0.0' WHERE version IS NULL OR version = ''")
                )
                connection.execute(
                    text("UPDATE skills SET title=name WHERE title IS NULL OR title = ''")
                )
            if table_name == "skill_invocations":
                connection.execute(
                    text(
                        "UPDATE skill_invocations SET started_at = created_at "
                        "WHERE started_at IS NULL"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE skill_invocations SET finished_at = updated_at "
                        "WHERE finished_at IS NULL"
                    )
                )
            if table_name == "connector_deliveries":
                connection.execute(
                    text(
                        "UPDATE connector_deliveries SET debug_payload='{}' "
                        "WHERE debug_payload IS NULL OR debug_payload = ''"
                    )
                )


def init_db() -> None:
    if engine.dialect.name != "sqlite":
        return
    target_metadata.create_all(bind=engine)
    _ensure_sqlite_columns()
