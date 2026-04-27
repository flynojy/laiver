"""add companion memory v2 storage primitives

Revision ID: 20260423_0006
Revises: 20260422_0005
Create Date: 2026-04-23 09:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260423_0006"
down_revision = "20260422_0005"
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
uuid_type = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "memory_episodes",
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("persona_id", uuid_type, nullable=True),
        sa.Column("conversation_id", uuid_type, nullable=True),
        sa.Column("source_message_id", uuid_type, nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("speaker_role", sa.String(length=40), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("structured_payload", json_type, nullable=False),
        sa.Column("summary_short", sa.String(length=500), nullable=True),
        sa.Column("summary_medium", sa.Text(), nullable=True),
        sa.Column("importance", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("emotional_weight", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("embedding_vector_id", sa.String(length=64), nullable=True),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_memory_episodes_conversation_id_conversations"),
        ),
        sa.ForeignKeyConstraint(
            ["persona_id"],
            ["personas.id"],
            name=op.f("fk_memory_episodes_persona_id_personas"),
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["messages.id"],
            name=op.f("fk_memory_episodes_source_message_id_messages"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_memory_episodes_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_episodes")),
    )
    op.create_index(op.f("ix_memory_episodes_conversation_id"), "memory_episodes", ["conversation_id"], unique=False)
    op.create_index(
        op.f("ix_memory_episodes_embedding_vector_id"),
        "memory_episodes",
        ["embedding_vector_id"],
        unique=False,
    )
    op.create_index(op.f("ix_memory_episodes_persona_id"), "memory_episodes", ["persona_id"], unique=False)
    op.create_index(
        op.f("ix_memory_episodes_source_message_id"),
        "memory_episodes",
        ["source_message_id"],
        unique=False,
    )
    op.create_index(op.f("ix_memory_episodes_source_ref"), "memory_episodes", ["source_ref"], unique=False)
    op.create_index(op.f("ix_memory_episodes_source_type"), "memory_episodes", ["source_type"], unique=False)
    op.create_index(op.f("ix_memory_episodes_user_id"), "memory_episodes", ["user_id"], unique=False)

    op.create_table(
        "memory_facts",
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("persona_id", uuid_type, nullable=True),
        sa.Column("fact_type", sa.String(length=80), nullable=False),
        sa.Column("subject_kind", sa.String(length=80), server_default=sa.text("'user'"), nullable=False),
        sa.Column("subject_ref", sa.String(length=160), nullable=True),
        sa.Column("predicate_key", sa.String(length=160), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_json", json_type, nullable=False),
        sa.Column("normalized_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), server_default=sa.text("'active'"), nullable=False),
        sa.Column("current_revision_id", uuid_type, nullable=True),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("importance", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("stability_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("reinforcement_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("source_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decay_policy", sa.String(length=80), server_default=sa.text("'default'"), nullable=False),
        sa.Column("sensitivity", sa.String(length=40), server_default=sa.text("'normal'"), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["persona_id"],
            ["personas.id"],
            name=op.f("fk_memory_facts_persona_id_personas"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_memory_facts_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_facts")),
    )
    op.create_index(
        op.f("ix_memory_facts_current_revision_id"),
        "memory_facts",
        ["current_revision_id"],
        unique=False,
    )
    op.create_index(op.f("ix_memory_facts_fact_type"), "memory_facts", ["fact_type"], unique=False)
    op.create_index(op.f("ix_memory_facts_normalized_key"), "memory_facts", ["normalized_key"], unique=False)
    op.create_index(op.f("ix_memory_facts_persona_id"), "memory_facts", ["persona_id"], unique=False)
    op.create_index(op.f("ix_memory_facts_predicate_key"), "memory_facts", ["predicate_key"], unique=False)
    op.create_index(op.f("ix_memory_facts_status"), "memory_facts", ["status"], unique=False)
    op.create_index(op.f("ix_memory_facts_subject_ref"), "memory_facts", ["subject_ref"], unique=False)
    op.create_index(op.f("ix_memory_facts_user_id"), "memory_facts", ["user_id"], unique=False)

    op.create_table(
        "user_profiles",
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("core_identity_json", json_type, nullable=False),
        sa.Column("communication_style_json", json_type, nullable=False),
        sa.Column("stable_preferences_json", json_type, nullable=False),
        sa.Column("boundaries_json", json_type, nullable=False),
        sa.Column("life_context_json", json_type, nullable=False),
        sa.Column("profile_summary", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("profile_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("source_fact_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_rebuilt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_profiles_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_profiles_user_id")),
    )
    op.create_index(op.f("ix_user_profiles_user_id"), "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "relationship_states",
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("persona_id", uuid_type, nullable=False),
        sa.Column("relationship_stage", sa.String(length=80), server_default=sa.text("'new'"), nullable=False),
        sa.Column("warmth_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("trust_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("familiarity_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("preferred_tone", sa.String(length=120), nullable=True),
        sa.Column("active_topics_json", json_type, nullable=False),
        sa.Column("recurring_rituals_json", json_type, nullable=False),
        sa.Column("recent_sensitivities_json", json_type, nullable=False),
        sa.Column("unresolved_tensions_json", json_type, nullable=False),
        sa.Column("last_meaningful_interaction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_repair_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["persona_id"],
            ["personas.id"],
            name=op.f("fk_relationship_states_persona_id_personas"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_relationship_states_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relationship_states")),
        sa.UniqueConstraint("user_id", "persona_id", name="uq_relationship_states_user_persona"),
    )
    op.create_index(op.f("ix_relationship_states_persona_id"), "relationship_states", ["persona_id"], unique=False)
    op.create_index(op.f("ix_relationship_states_user_id"), "relationship_states", ["user_id"], unique=False)

    op.create_table(
        "memory_revisions",
        sa.Column("fact_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("op", sa.String(length=40), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("value_json", json_type, nullable=False),
        sa.Column("confidence_delta", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("source_episode_id", uuid_type, nullable=True),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.Column("conflict_group_id", sa.String(length=160), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_type", sa.String(length=40), server_default=sa.text("'system'"), nullable=False),
        sa.Column("reason_codes", json_type, nullable=False),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["memory_facts.id"],
            name=op.f("fk_memory_revisions_fact_id_memory_facts"),
        ),
        sa.ForeignKeyConstraint(
            ["source_episode_id"],
            ["memory_episodes.id"],
            name=op.f("fk_memory_revisions_source_episode_id_memory_episodes"),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["memory_revisions.id"],
            name=op.f("fk_memory_revisions_supersedes_revision_id_memory_revisions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_revisions")),
    )
    op.create_index(
        op.f("ix_memory_revisions_conflict_group_id"),
        "memory_revisions",
        ["conflict_group_id"],
        unique=False,
    )
    op.create_index(op.f("ix_memory_revisions_fact_id"), "memory_revisions", ["fact_id"], unique=False)
    op.create_index(op.f("ix_memory_revisions_op"), "memory_revisions", ["op"], unique=False)
    op.create_index(
        op.f("ix_memory_revisions_source_episode_id"),
        "memory_revisions",
        ["source_episode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memory_revisions_supersedes_revision_id"),
        "memory_revisions",
        ["supersedes_revision_id"],
        unique=False,
    )

    op.create_table(
        "memory_candidates",
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("persona_id", uuid_type, nullable=True),
        sa.Column("episode_id", uuid_type, nullable=False),
        sa.Column("candidate_type", sa.String(length=80), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.String(length=255), nullable=False),
        sa.Column("proposed_value_json", json_type, nullable=False),
        sa.Column("proposed_action", sa.String(length=40), server_default=sa.text("'create'"), nullable=False),
        sa.Column("salience_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("sensitivity", sa.String(length=40), server_default=sa.text("'normal'"), nullable=False),
        sa.Column("reason_codes_json", json_type, nullable=False),
        sa.Column("auto_commit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=40), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reviewer_type", sa.String(length=40), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["memory_episodes.id"],
            name=op.f("fk_memory_candidates_episode_id_memory_episodes"),
        ),
        sa.ForeignKeyConstraint(
            ["persona_id"],
            ["personas.id"],
            name=op.f("fk_memory_candidates_persona_id_personas"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_memory_candidates_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_candidates")),
    )
    op.create_index(
        op.f("ix_memory_candidates_candidate_type"),
        "memory_candidates",
        ["candidate_type"],
        unique=False,
    )
    op.create_index(op.f("ix_memory_candidates_episode_id"), "memory_candidates", ["episode_id"], unique=False)
    op.create_index(
        op.f("ix_memory_candidates_normalized_key"),
        "memory_candidates",
        ["normalized_key"],
        unique=False,
    )
    op.create_index(op.f("ix_memory_candidates_persona_id"), "memory_candidates", ["persona_id"], unique=False)
    op.create_index(op.f("ix_memory_candidates_user_id"), "memory_candidates", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_candidates_user_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_persona_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_normalized_key"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_episode_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_candidate_type"), table_name="memory_candidates")
    op.drop_table("memory_candidates")

    op.drop_index(op.f("ix_memory_revisions_supersedes_revision_id"), table_name="memory_revisions")
    op.drop_index(op.f("ix_memory_revisions_source_episode_id"), table_name="memory_revisions")
    op.drop_index(op.f("ix_memory_revisions_op"), table_name="memory_revisions")
    op.drop_index(op.f("ix_memory_revisions_fact_id"), table_name="memory_revisions")
    op.drop_index(op.f("ix_memory_revisions_conflict_group_id"), table_name="memory_revisions")
    op.drop_table("memory_revisions")

    op.drop_index(op.f("ix_relationship_states_user_id"), table_name="relationship_states")
    op.drop_index(op.f("ix_relationship_states_persona_id"), table_name="relationship_states")
    op.drop_table("relationship_states")

    op.drop_index(op.f("ix_user_profiles_user_id"), table_name="user_profiles")
    op.drop_table("user_profiles")

    op.drop_index(op.f("ix_memory_facts_user_id"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_subject_ref"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_status"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_predicate_key"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_persona_id"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_normalized_key"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_fact_type"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_current_revision_id"), table_name="memory_facts")
    op.drop_table("memory_facts")

    op.drop_index(op.f("ix_memory_episodes_user_id"), table_name="memory_episodes")
    op.drop_index(op.f("ix_memory_episodes_source_type"), table_name="memory_episodes")
    op.drop_index(op.f("ix_memory_episodes_source_ref"), table_name="memory_episodes")
    op.drop_index(op.f("ix_memory_episodes_source_message_id"), table_name="memory_episodes")
    op.drop_index(op.f("ix_memory_episodes_persona_id"), table_name="memory_episodes")
    op.drop_index(op.f("ix_memory_episodes_embedding_vector_id"), table_name="memory_episodes")
    op.drop_index(op.f("ix_memory_episodes_conversation_id"), table_name="memory_episodes")
    op.drop_table("memory_episodes")
