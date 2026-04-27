"""add local fine-tune job table

Revision ID: 20260422_0004
Revises: 20260422_0003
Create Date: 2026-04-22 00:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260422_0004"
down_revision = "20260422_0003"
branch_labels = None
depends_on = None


jsonb = postgresql.JSONB(astext_type=sa.Text())
fine_tune_backend = sa.Enum("local_lora", "local_qlora", name="finetunebackend", native_enum=False)
fine_tune_status = sa.Enum(
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
    name="finetunejobstatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "fine_tune_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_speaker", sa.String(length=120), nullable=False),
        sa.Column("backend", fine_tune_backend, nullable=False),
        sa.Column("status", fine_tune_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("base_model", sa.String(length=160), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=False, server_default=sa.text("6")),
        sa.Column("source_message_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("train_examples", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("validation_examples", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("test_examples", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("dataset_path", sa.String(length=500), nullable=False),
        sa.Column("config_path", sa.String(length=500), nullable=False),
        sa.Column("output_dir", sa.String(length=500), nullable=False),
        sa.Column("launcher_command", sa.Text(), nullable=False),
        sa.Column("training_config", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dataset_stats", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("artifact_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"], name=op.f("fk_fine_tune_jobs_import_id_imports")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_fine_tune_jobs_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fine_tune_jobs")),
    )
    op.create_index(op.f("ix_fine_tune_jobs_import_id"), "fine_tune_jobs", ["import_id"], unique=False)
    op.create_index(op.f("ix_fine_tune_jobs_user_id"), "fine_tune_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fine_tune_jobs_user_id"), table_name="fine_tune_jobs")
    op.drop_index(op.f("ix_fine_tune_jobs_import_id"), table_name="fine_tune_jobs")
    op.drop_table("fine_tune_jobs")
