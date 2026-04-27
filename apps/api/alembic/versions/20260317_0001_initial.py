"""initial schema

Revision ID: 20260317_0001
Revises:
Create Date: 2026-03-17 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260317_0001"
down_revision = None
branch_labels = None
depends_on = None


message_role = sa.Enum("system", "user", "assistant", "tool", name="messagerole", native_enum=False)
import_source_type = sa.Enum("txt", "csv", "json", name="importsourcetype", native_enum=False)
import_status = sa.Enum("previewed", "committed", "failed", name="importstatus", native_enum=False)
memory_type = sa.Enum("session", "episodic", "semantic", "instruction", name="memorytype", native_enum=False)
connector_platform = sa.Enum("feishu", name="connectorplatform", native_enum=False)
connector_status = sa.Enum("inactive", "active", "error", name="connectorstatus", native_enum=False)
provider_type = sa.Enum("deepseek", name="providertype", native_enum=False)
skill_status = sa.Enum("disabled", "active", name="skillstatus", native_enum=False)
conversation_status = sa.Enum("active", "archived", name="conversationstatus", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("source_type", import_source_type, nullable=False),
        sa.Column("status", import_status, nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("preview", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("normalized_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_imports_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imports")),
    )
    op.create_index(op.f("ix_imports_user_id"), "imports", ["user_id"], unique=False)

    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tone", sa.String(length=120), nullable=False),
        sa.Column("verbosity", sa.String(length=60), nullable=False),
        sa.Column("common_phrases", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("common_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("response_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("relationship_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_import_id"], ["imports.id"], name=op.f("fk_personas_source_import_id_imports")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_personas_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_personas")),
    )
    op.create_index(op.f("ix_personas_source_import_id"), "personas", ["source_import_id"], unique=False)
    op.create_index(op.f("ix_personas_user_id"), "personas", ["user_id"], unique=False)

    op.create_table(
        "normalized_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("speaker", sa.String(length=120), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"], name=op.f("fk_normalized_messages_import_id_imports")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_normalized_messages")),
        sa.UniqueConstraint("import_id", "sequence_index", name="uq_normalized_messages_import_sequence"),
    )
    op.create_index(op.f("ix_normalized_messages_import_id"), "normalized_messages", ["import_id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(length=80), nullable=False, server_default=sa.text("'web'")),
        sa.Column("status", conversation_status, nullable=False, server_default=sa.text("'active'")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], name=op.f("fk_conversations_persona_id_personas")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_conversations_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(op.f("ix_conversations_persona_id"), "conversations", ["persona_id"], unique=False)
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("tool_name", sa.String(length=120), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sequence_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_messages_conversation_id_conversations")),
        sa.ForeignKeyConstraint(["parent_message_id"], ["messages.id"], name=op.f("fk_messages_parent_message_id_messages")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("runtime_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", skill_status, nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_skills_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint("slug", name=op.f("uq_skills_slug")),
    )
    op.create_index(op.f("ix_skills_user_id"), "skills", ["user_id"], unique=False)

    op.create_table(
        "connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", connector_platform, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", connector_status, nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_connectors_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_connectors")),
    )
    op.create_index(op.f("ix_connectors_user_id"), "connectors", ["user_id"], unique=False)

    op.create_table(
        "model_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("provider_type", provider_type, nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("api_key_ref", sa.String(length=255), nullable=True),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_model_providers_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_providers")),
    )
    op.create_index(op.f("ix_model_providers_user_id"), "model_providers", ["user_id"], unique=False)

    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("memory_type", memory_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False, server_default=sa.text("'hash-embedding-v1'")),
        sa.Column("vector_id", sa.String(length=64), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name=op.f("fk_memories_conversation_id_conversations")),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], name=op.f("fk_memories_persona_id_personas")),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], name=op.f("fk_memories_source_message_id_messages")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_memories_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memories")),
        sa.UniqueConstraint("user_id", "memory_type", "content_hash", name="uq_memories_hash"),
        sa.UniqueConstraint("vector_id", name=op.f("uq_memories_vector_id")),
    )
    op.create_index(op.f("ix_memories_conversation_id"), "memories", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_memories_memory_type"), "memories", ["memory_type"], unique=False)
    op.create_index(op.f("ix_memories_persona_id"), "memories", ["persona_id"], unique=False)
    op.create_index(op.f("ix_memories_source_message_id"), "memories", ["source_message_id"], unique=False)
    op.create_index(op.f("ix_memories_user_id"), "memories", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memories_user_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_source_message_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_persona_id"), table_name="memories")
    op.drop_index(op.f("ix_memories_memory_type"), table_name="memories")
    op.drop_index(op.f("ix_memories_conversation_id"), table_name="memories")
    op.drop_table("memories")
    op.drop_index(op.f("ix_model_providers_user_id"), table_name="model_providers")
    op.drop_table("model_providers")
    op.drop_index(op.f("ix_connectors_user_id"), table_name="connectors")
    op.drop_table("connectors")
    op.drop_index(op.f("ix_skills_user_id"), table_name="skills")
    op.drop_table("skills")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_persona_id"), table_name="conversations")
    op.drop_table("conversations")
    op.drop_index(op.f("ix_normalized_messages_import_id"), table_name="normalized_messages")
    op.drop_table("normalized_messages")
    op.drop_index(op.f("ix_personas_user_id"), table_name="personas")
    op.drop_index(op.f("ix_personas_source_import_id"), table_name="personas")
    op.drop_table("personas")
    op.drop_index(op.f("ix_imports_user_id"), table_name="imports")
    op.drop_table("imports")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
