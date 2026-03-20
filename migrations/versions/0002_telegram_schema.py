"""Telegram bot schema — tables, columns, triggers, and views.

Revision ID: 0002
Revises: 0001
Create Date: 2025-10-02 00:00:00.000000

NOTE: If you already ran migrations/versions/001_telegram_bot_schema.sql manually,
mark this migration as applied without re-running it:
    alembic stamp 0002

On a fresh database, this migration runs automatically after 0001.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend users table with Telegram columns
    op.add_column("users", sa.Column("telegram_chat_id", sa.BigInteger(), unique=True, nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("telegram_linked_at", sa.DateTime(), nullable=True))
    op.create_index("idx_users_telegram_chat", "users", ["telegram_chat_id"],
                    postgresql_where=sa.text("telegram_chat_id IS NOT NULL"))

    # telegram_preferences
    op.create_table(
        "telegram_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("alert_types", postgresql.ARRAY(sa.Text()),
                  server_default="{high_confidence,risk_breach,large_position}"),
        sa.Column("signal_filter", sa.String(20), server_default="all"),
        sa.Column("notification_hours", postgresql.ARRAY(sa.Integer()),
                  server_default="{9,10,11,14,15}"),
        sa.Column("watchlist", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("language", sa.String(10), server_default="id"),
        sa.Column("timezone", sa.String(50), server_default="Asia/Jakarta"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_telegram_prefs_user", "telegram_preferences", ["user_id"])

    # bot_command_log
    op.create_table(
        "bot_command_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("command", sa.String(100), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), nullable=True),
        sa.Column("response_status", sa.String(20), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_bot_log_user_time", "bot_command_log", ["user_id", "executed_at"])
    op.create_index("idx_bot_log_command_time", "bot_command_log", ["command", "executed_at"])

    # pending_transactions
    op.create_table(
        "pending_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("stock_code", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("confirmation_code", sa.String(20), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("meta_data", postgresql.JSONB(), nullable=True),
    )
    op.create_index("idx_pending_trans_user", "pending_transactions", ["user_id", "status"])
    op.create_index("idx_pending_trans_code", "pending_transactions", ["confirmation_code"],
                    postgresql_where=sa.text("status = 'pending'"))
    op.create_index("idx_pending_trans_expires", "pending_transactions", ["expires_at"],
                    postgresql_where=sa.text("status = 'pending'"))

    # telegram_auth_tokens
    op.create_table(
        "telegram_auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token", sa.String(100), unique=True, nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
    )
    op.create_index("idx_telegram_auth_token", "telegram_auth_tokens", ["token"],
                    postgresql_where=sa.text("status = 'pending'"))
    op.create_index("idx_telegram_auth_chat", "telegram_auth_tokens",
                    ["telegram_chat_id", "status"])

    # Triggers and views are created via raw SQL (Alembic supports this)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_telegram_preferences_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER telegram_preferences_update_timestamp
        BEFORE UPDATE ON telegram_preferences
        FOR EACH ROW EXECUTE FUNCTION update_telegram_preferences_timestamp();

        CREATE OR REPLACE FUNCTION expire_pending_transactions()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.expires_at < NOW() AND NEW.status = 'pending' THEN
                NEW.status = 'expired';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER pending_transactions_auto_expire
        BEFORE UPDATE ON pending_transactions
        FOR EACH ROW EXECUTE FUNCTION expire_pending_transactions();

        CREATE OR REPLACE VIEW active_telegram_users AS
        SELECT u.id, u.username, u.email, u.telegram_chat_id, u.telegram_username,
               u.telegram_linked_at, tp.language, tp.watchlist,
               COUNT(DISTINCT bcl.id) AS command_count_30d
        FROM users u
        LEFT JOIN telegram_preferences tp ON u.id = tp.user_id
        LEFT JOIN bot_command_log bcl ON u.id = bcl.user_id
            AND bcl.executed_at > NOW() - INTERVAL '30 days'
        WHERE u.telegram_chat_id IS NOT NULL
        GROUP BY u.id, tp.language, tp.watchlist;

        CREATE OR REPLACE VIEW bot_command_analytics AS
        SELECT DATE(executed_at) AS date, command, response_status,
               COUNT(*) AS count,
               AVG(response_time_ms) AS avg_response_time_ms,
               PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_response_time_ms
        FROM bot_command_log
        WHERE executed_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(executed_at), command, response_status
        ORDER BY date DESC, count DESC;

        INSERT INTO telegram_preferences (user_id)
        SELECT id FROM users ON CONFLICT (user_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DROP VIEW IF EXISTS bot_command_analytics;
        DROP VIEW IF EXISTS active_telegram_users;
        DROP TRIGGER IF EXISTS pending_transactions_auto_expire ON pending_transactions;
        DROP TRIGGER IF EXISTS telegram_preferences_update_timestamp ON telegram_preferences;
        DROP FUNCTION IF EXISTS expire_pending_transactions();
        DROP FUNCTION IF EXISTS update_telegram_preferences_timestamp();
    """)
    op.drop_table("telegram_auth_tokens")
    op.drop_table("pending_transactions")
    op.drop_table("bot_command_log")
    op.drop_table("telegram_preferences")
    op.drop_index("idx_users_telegram_chat", table_name="users")
    op.drop_column("users", "telegram_linked_at")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_chat_id")
