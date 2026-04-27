"""align runtime schema with current MVP services

Revision ID: 20260404_0002
Revises: 20260317_0001
Create Date: 2026-04-04 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260404_0002"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None


jsonb = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column(
        "personas",
        sa.Column(
            "confidence_scores",
            jsonb,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "personas",
        sa.Column(
            "evidence_samples",
            jsonb,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column(
        "memories",
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
    )
    op.execute("UPDATE memories SET confidence_score = COALESCE(importance_score, 0.5)")

    op.add_column(
        "skills",
        sa.Column(
            "version",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'1.0.0'"),
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "title",
            sa.String(length=160),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.execute("UPDATE skills SET version = '1.0.0' WHERE version IS NULL OR version = ''")
    op.execute("UPDATE skills SET title = name WHERE title IS NULL OR title = ''")
    op.drop_column("skills", "input_schema")
    op.drop_column("skills", "output_schema")

    op.create_table(
        "skill_invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_slug", sa.String(length=120), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("trace_id", sa.String(length=80), nullable=False),
        sa.Column("trigger_source", sa.String(length=40), nullable=False, server_default=sa.text("'planner'")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_payload", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_payload", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=40), nullable=False, server_default=sa.text("'success'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_skill_invocations_conversation_id_conversations")),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], name=op.f("fk_skill_invocations_message_id_messages")),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_skill_invocations_skill_id_skills")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_invocations")),
    )
    op.create_index(op.f("ix_skill_invocations_skill_id"), "skill_invocations", ["skill_id"], unique=False)
    op.create_index(op.f("ix_skill_invocations_skill_slug"), "skill_invocations", ["skill_slug"], unique=False)
    op.create_index(op.f("ix_skill_invocations_trace_id"), "skill_invocations", ["trace_id"], unique=False)

    op.create_table(
        "connector_conversation_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_key", sa.String(length=255), nullable=False),
        sa.Column("external_chat_id", sa.String(length=255), nullable=True),
        sa.Column("external_user_id", sa.String(length=255), nullable=True),
        sa.Column("internal_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("default_persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("memory_scope", sa.String(length=40), nullable=False, server_default=sa.text("'chat'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["connector_id"], ["connectors.id"], name=op.f("fk_connector_conversation_mappings_connector_id_connectors")),
        sa.ForeignKeyConstraint(["default_persona_id"], ["personas.id"], name=op.f("fk_connector_conversation_mappings_default_persona_id_personas")),
        sa.ForeignKeyConstraint(["internal_conversation_id"], ["conversations.id"], name=op.f("fk_connector_conversation_mappings_internal_conversation_id_conversations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_connector_conversation_mappings")),
        sa.UniqueConstraint("connector_id", "conversation_key", name="uq_connector_conversation_mappings_key"),
    )
    op.create_index(
        op.f("ix_connector_conversation_mappings_connector_id"),
        "connector_conversation_mappings",
        ["connector_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_connector_conversation_mappings_conversation_key"),
        "connector_conversation_mappings",
        ["conversation_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_connector_conversation_mappings_default_persona_id"),
        "connector_conversation_mappings",
        ["default_persona_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_connector_conversation_mappings_external_chat_id"),
        "connector_conversation_mappings",
        ["external_chat_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_connector_conversation_mappings_external_user_id"),
        "connector_conversation_mappings",
        ["external_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_connector_conversation_mappings_internal_conversation_id"),
        "connector_conversation_mappings",
        ["internal_conversation_id"],
        unique=False,
    )

    op.create_table(
        "connector_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_type", sa.String(length=40), nullable=False),
        sa.Column("trace_id", sa.String(length=80), nullable=False),
        sa.Column("conversation_mapping_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("internal_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("inbound_message", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalized_input", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("agent_response", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("outbound_response", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("debug_payload", jsonb, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("delivery_status", sa.String(length=40), nullable=False, server_default=sa.text("'received'")),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default=sa.text("'mock'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["connector_id"], ["connectors.id"], name=op.f("fk_connector_deliveries_connector_id_connectors")),
        sa.ForeignKeyConstraint(["conversation_mapping_id"], ["connector_conversation_mappings.id"], name=op.f("fk_connector_deliveries_conversation_mapping_id_connector_conversation_mappings")),
        sa.ForeignKeyConstraint(["internal_conversation_id"], ["conversations.id"], name=op.f("fk_connector_deliveries_internal_conversation_id_conversations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_connector_deliveries")),
        sa.UniqueConstraint("connector_id", "external_message_id", name="uq_connector_deliveries_external_message"),
    )
    op.create_index(op.f("ix_connector_deliveries_connector_id"), "connector_deliveries", ["connector_id"], unique=False)
    op.create_index(op.f("ix_connector_deliveries_conversation_mapping_id"), "connector_deliveries", ["conversation_mapping_id"], unique=False)
    op.create_index(op.f("ix_connector_deliveries_internal_conversation_id"), "connector_deliveries", ["internal_conversation_id"], unique=False)
    op.create_index(op.f("ix_connector_deliveries_trace_id"), "connector_deliveries", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_connector_deliveries_trace_id"), table_name="connector_deliveries")
    op.drop_index(op.f("ix_connector_deliveries_internal_conversation_id"), table_name="connector_deliveries")
    op.drop_index(op.f("ix_connector_deliveries_conversation_mapping_id"), table_name="connector_deliveries")
    op.drop_index(op.f("ix_connector_deliveries_connector_id"), table_name="connector_deliveries")
    op.drop_table("connector_deliveries")

    op.drop_index(
        op.f("ix_connector_conversation_mappings_internal_conversation_id"),
        table_name="connector_conversation_mappings",
    )
    op.drop_index(
        op.f("ix_connector_conversation_mappings_external_user_id"),
        table_name="connector_conversation_mappings",
    )
    op.drop_index(
        op.f("ix_connector_conversation_mappings_external_chat_id"),
        table_name="connector_conversation_mappings",
    )
    op.drop_index(
        op.f("ix_connector_conversation_mappings_default_persona_id"),
        table_name="connector_conversation_mappings",
    )
    op.drop_index(
        op.f("ix_connector_conversation_mappings_conversation_key"),
        table_name="connector_conversation_mappings",
    )
    op.drop_index(
        op.f("ix_connector_conversation_mappings_connector_id"),
        table_name="connector_conversation_mappings",
    )
    op.drop_table("connector_conversation_mappings")

    op.drop_index(op.f("ix_skill_invocations_trace_id"), table_name="skill_invocations")
    op.drop_index(op.f("ix_skill_invocations_skill_slug"), table_name="skill_invocations")
    op.drop_index(op.f("ix_skill_invocations_skill_id"), table_name="skill_invocations")
    op.drop_table("skill_invocations")

    op.add_column(
        "skills",
        sa.Column(
            "output_schema",
            jsonb,
            autoincrement=False,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "input_schema",
            jsonb,
            autoincrement=False,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.drop_column("skills", "title")
    op.drop_column("skills", "version")

    op.drop_column("memories", "confidence_score")
    op.drop_column("personas", "evidence_samples")
    op.drop_column("personas", "confidence_scores")
