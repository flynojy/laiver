"""add local adapter provider type and fine-tune provider linkage

Revision ID: 20260422_0005
Revises: 20260422_0004
Create Date: 2026-04-22 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260422_0005"
down_revision = "20260422_0004"
branch_labels = None
depends_on = None


old_provider_type = sa.Enum(
    "deepseek",
    "openai_compatible",
    "ollama",
    name="providertype",
    native_enum=False,
)
new_provider_type = sa.Enum(
    "deepseek",
    "openai_compatible",
    "ollama",
    "local_adapter",
    name="providertype",
    native_enum=False,
)


def upgrade() -> None:
    op.alter_column(
        "model_providers",
        "provider_type",
        existing_type=old_provider_type,
        type_=new_provider_type,
        existing_nullable=False,
        postgresql_using="provider_type::text",
    )
    op.add_column(
        "fine_tune_jobs",
        sa.Column("registered_provider_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_fine_tune_jobs_registered_provider_id"),
        "fine_tune_jobs",
        ["registered_provider_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_fine_tune_jobs_registered_provider_id_model_providers"),
        "fine_tune_jobs",
        "model_providers",
        ["registered_provider_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_fine_tune_jobs_registered_provider_id_model_providers"),
        "fine_tune_jobs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_fine_tune_jobs_registered_provider_id"), table_name="fine_tune_jobs")
    op.drop_column("fine_tune_jobs", "registered_provider_id")
    op.execute("DELETE FROM model_providers WHERE provider_type = 'local_adapter'")
    op.alter_column(
        "model_providers",
        "provider_type",
        existing_type=new_provider_type,
        type_=old_provider_type,
        existing_nullable=False,
        postgresql_using="provider_type::text",
    )
