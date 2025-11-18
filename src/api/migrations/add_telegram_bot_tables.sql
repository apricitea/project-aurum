-- Migration: Add Telegram Bot Support Tables
-- Description: Adds necessary tables for Telegram bot authentication and command logging
-- Date: 2025-10-02

-- Add Telegram fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_linked_at TIMESTAMP;

-- Create index on telegram_chat_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_telegram_chat_id ON users(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

-- Telegram authentication tokens table
CREATE TABLE IF NOT EXISTS telegram_auth_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    telegram_chat_id BIGINT NOT NULL,
    telegram_username VARCHAR(100),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- Indexes for telegram_auth_tokens
CREATE INDEX IF NOT EXISTS idx_telegram_auth_tokens_hash ON telegram_auth_tokens(token_hash) WHERE used_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_telegram_auth_tokens_chat_id ON telegram_auth_tokens(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_telegram_auth_tokens_expires ON telegram_auth_tokens(expires_at) WHERE used_at IS NULL;

-- Telegram user preferences table
CREATE TABLE IF NOT EXISTS telegram_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    alert_types TEXT[] DEFAULT ARRAY['high_confidence_signal', 'risk_limit_breach', 'large_position'],
    signal_filter VARCHAR(20) DEFAULT 'all',  -- 'all', 'buy_only', 'sell_only', 'high_confidence'
    notification_hours INTEGER[] DEFAULT ARRAY[9, 10, 11, 14, 15],  -- WIB hours
    watchlist TEXT[] DEFAULT ARRAY[]::TEXT[],  -- Stock codes
    language VARCHAR(10) DEFAULT 'id',  -- 'id' (Indonesian) or 'en' (English)
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for telegram_preferences
CREATE INDEX IF NOT EXISTS idx_telegram_prefs_user ON telegram_preferences(user_id);

-- Bot command log table for audit trail
CREATE TABLE IF NOT EXISTS bot_command_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    telegram_chat_id BIGINT NOT NULL,
    command VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}',
    response_status VARCHAR(20) NOT NULL,  -- 'success', 'error', 'unauthorized'
    response_time_ms INTEGER,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for bot_command_log
CREATE INDEX IF NOT EXISTS idx_bot_log_user_time ON bot_command_log(user_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_log_chat_id ON bot_command_log(telegram_chat_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_log_command ON bot_command_log(command, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_log_status ON bot_command_log(response_status, executed_at DESC);

-- Pending transactions table for 2-step confirmation (future use)
CREATE TABLE IF NOT EXISTS pending_transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,  -- 'buy', 'sell', 'update'
    stock_code VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price FLOAT NOT NULL,
    confirmation_code VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'confirmed', 'expired', 'cancelled'
    CONSTRAINT valid_transaction_expiry CHECK (expires_at > created_at),
    CONSTRAINT valid_quantity CHECK (quantity >= 0),
    CONSTRAINT valid_price CHECK (price > 0)
);

-- Indexes for pending_transactions
CREATE INDEX IF NOT EXISTS idx_pending_trans_user ON pending_transactions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_pending_trans_code ON pending_transactions(confirmation_code) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_pending_trans_expires ON pending_transactions(expires_at) WHERE status = 'pending';

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for telegram_preferences
DROP TRIGGER IF EXISTS update_telegram_preferences_updated_at ON telegram_preferences;
CREATE TRIGGER update_telegram_preferences_updated_at
    BEFORE UPDATE ON telegram_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up expired auth tokens (run periodically)
CREATE OR REPLACE FUNCTION cleanup_expired_auth_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM telegram_auth_tokens
    WHERE expires_at < NOW() AND used_at IS NULL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired pending transactions
CREATE OR REPLACE FUNCTION cleanup_expired_transactions()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE pending_transactions
    SET status = 'expired'
    WHERE expires_at < NOW() AND status = 'pending';

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE telegram_auth_tokens IS 'Stores authentication tokens for linking Telegram accounts';
COMMENT ON TABLE telegram_preferences IS 'Stores user preferences for Telegram bot notifications';
COMMENT ON TABLE bot_command_log IS 'Audit log for all bot command executions';
COMMENT ON TABLE pending_transactions IS 'Stores pending transactions requiring 2-step confirmation';

COMMENT ON COLUMN users.telegram_chat_id IS 'Telegram chat ID linked to this user account';
COMMENT ON COLUMN users.telegram_username IS 'Telegram username (without @)';
COMMENT ON COLUMN users.telegram_linked_at IS 'Timestamp when Telegram account was linked';

-- Grant necessary permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE ON telegram_auth_tokens TO trading_app;
-- GRANT SELECT, INSERT, UPDATE ON telegram_preferences TO trading_app;
-- GRANT SELECT, INSERT ON bot_command_log TO trading_app;
-- GRANT SELECT, INSERT, UPDATE ON pending_transactions TO trading_app;

-- Create view for active Telegram users
CREATE OR REPLACE VIEW active_telegram_users AS
SELECT
    u.id,
    u.username,
    u.email,
    u.role,
    u.telegram_chat_id,
    u.telegram_username,
    u.telegram_linked_at,
    u.last_login,
    tp.notifications_enabled,
    tp.language,
    tp.alert_types,
    tp.watchlist
FROM users u
LEFT JOIN telegram_preferences tp ON u.id = tp.user_id
WHERE u.telegram_chat_id IS NOT NULL
AND u.is_active = TRUE;

COMMENT ON VIEW active_telegram_users IS 'View of all users with active Telegram links';

-- Migration complete
-- To rollback this migration, run:
-- DROP VIEW IF EXISTS active_telegram_users;
-- DROP FUNCTION IF EXISTS cleanup_expired_transactions();
-- DROP FUNCTION IF EXISTS cleanup_expired_auth_tokens();
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
-- DROP TABLE IF EXISTS pending_transactions;
-- DROP TABLE IF EXISTS bot_command_log;
-- DROP TABLE IF EXISTS telegram_preferences;
-- DROP TABLE IF EXISTS telegram_auth_tokens;
-- ALTER TABLE users DROP COLUMN IF EXISTS telegram_chat_id;
-- ALTER TABLE users DROP COLUMN IF EXISTS telegram_username;
-- ALTER TABLE users DROP COLUMN IF EXISTS telegram_linked_at;
