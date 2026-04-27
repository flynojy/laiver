"""extend model provider types for external and local runtimes

Revision ID: 20260422_0003
Revises: 20260404_0002
Create Date: 2026-04-22 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_0003"
down_revision = "20260404_0002"
branch_labels = None
depends_on = None


old_provider_type = sa.Enum("deepseek", name="providertype", native_enum=False)
new_provider_type = sa.Enum(
    "deepseek",
    "openai_compatible",
    "ollama",
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


def downgrade() -> None:
    op.execute(
        "DELETE FROM model_providers WHERE provider_type IN ('openai_compatible', 'ollama')"
    )
    op.alter_column(
        "model_providers",
        "provider_type",
        existing_type=new_provider_type,
        type_=old_provider_type,
        existing_nullable=False,
        postgresql_using="provider_type::text",
    )
