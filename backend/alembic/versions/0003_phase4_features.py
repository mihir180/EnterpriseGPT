"""phase 4 - departments, document ACL, permissions, analytics columns

Revision ID: 0003_phase4_features
Revises: 0002_add_chat_queries
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_phase4_features"
down_revision = "0002_add_chat_queries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    department_enum = postgresql.ENUM(
        "hr", "legal", "technical", "general", name="department"
    )
    department_enum.create(op.get_bind(), checkfirst=True)

    # --- users: department (drives agent routing + document ACL) ---
    op.add_column(
        "users",
        sa.Column(
            "department",
            postgresql.ENUM(
                "hr", "legal", "technical", "general",
                name="department", create_type=False,
            ),
            nullable=False,
            server_default="general",
        ),
    )

    # --- documents: ACL. Empty array = visible to every authenticated user. ---
    op.add_column(
        "documents",
        sa.Column(
            "allowed_departments",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )

    # --- document_permissions: explicit per-user grants that override department ACL ---
    op.create_table(
        "document_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "user_id", name="uq_document_permission"),
    )
    op.create_index(
        "ix_document_permissions_document_id", "document_permissions", ["document_id"]
    )
    op.create_index(
        "ix_document_permissions_user_id", "document_permissions", ["user_id"]
    )

    # --- chat_queries: which agent/department answered + retrieval mode, for analytics ---
    op.add_column(
        "chat_queries",
        sa.Column(
            "department",
            postgresql.ENUM(
                "hr", "legal", "technical", "general",
                name="department", create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "chat_queries",
        sa.Column("agent_used", sa.String(50), nullable=True),
    )
    op.add_column(
        "chat_queries",
        sa.Column("retrieval_mode", sa.String(20), nullable=False, server_default="hybrid"),
    )


def downgrade() -> None:
    op.drop_column("chat_queries", "retrieval_mode")
    op.drop_column("chat_queries", "agent_used")
    op.drop_column("chat_queries", "department")

    op.drop_index("ix_document_permissions_user_id", table_name="document_permissions")
    op.drop_index("ix_document_permissions_document_id", table_name="document_permissions")
    op.drop_table("document_permissions")

    op.drop_column("documents", "allowed_departments")
    op.drop_column("users", "department")

    postgresql.ENUM(name="department").drop(op.get_bind(), checkfirst=True)
