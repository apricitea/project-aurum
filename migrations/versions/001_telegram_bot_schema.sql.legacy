-- Migration: 001_telegram_bot_schema
-- Description: Add Telegram bot functionality tables and columns
-- Date: 2025-10-02
-- Author: Claude AI

-- ============================================================================
-- PART 1: ALTER EXISTING USERS TABLE
-- ============================================================================

-- Add Telegram-related columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT UNIQUE,
ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(100),
ADD COLUMN IF NOT EXISTS telegram_linked_at TIMESTAMP;

-- Create index for faster telegram lookups
CREATE INDEX IF NOT EXISTS idx_users_telegram_chat
ON users(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

-- ============================================================================
-- PART 2: TELEGRAM PREFERENCES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS telegram_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Alert configuration
    alert_types TEXT[] DEFAULT ARRAY['high_confidence', 'risk_breach', 'large_position'],
    signal_filter VARCHAR(20) DEFAULT 'all',  -- 'all', 'buy_only', 'sell_only', 'high_confidence'
    notification_hours INTEGER[] DEFAULT ARRAY[9, 10, 11, 14, 15],  -- WIB hours

    -- Watchlist
    watchlist TEXT[] DEFAULT ARRAY[]::TEXT[],  -- ['BBCA.JK', 'BMRI.JK', 'TLKM.JK']

    -- Localization
    language VARCHAR(10) DEFAULT 'id',  -- 'id' (Indonesian) or 'en' (English)
    timezone VARCHAR(50) DEFAULT 'Asia/Jakarta',

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure one preference per user
    UNIQUE(user_id)
);

-- Indexes for telegram_preferences
CREATE INDEX IF NOT EXISTS idx_telegram_prefs_user
ON telegram_preferences(user_id);

-- ============================================================================
-- PART 3: BOT COMMAND LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS bot_command_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    telegram_chat_id BIGINT NOT NULL,

    -- Command details
    command VARCHAR(100) NOT NULL,
    parameters JSONB,

    -- Response details
    response_status VARCHAR(20) NOT NULL,  -- 'success', 'error', 'unauthorized', 'rate_limited'
    response_time_ms INTEGER,
    error_message TEXT,

    -- Metadata
    executed_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Indexes for bot_command_log (for analytics and debugging)
CREATE INDEX IF NOT EXISTS idx_bot_log_user_time
ON bot_command_log(user_id, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_bot_log_command_time
ON bot_command_log(command, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_bot_log_status_time
ON bot_command_log(response_status, executed_at DESC)
WHERE response_status IN ('error', 'unauthorized');

-- Partition by month for performance (optional, for high-volume systems)
-- ALTER TABLE bot_command_log PARTITION BY RANGE (executed_at);

-- ============================================================================
-- PART 4: PENDING TRANSACTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS pending_transactions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Transaction details
    transaction_type VARCHAR(20) NOT NULL,  -- 'buy', 'sell', 'update'
    stock_code VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price FLOAT NOT NULL,

    -- Confirmation details
    confirmation_code VARCHAR(20) UNIQUE NOT NULL,

    -- Timing
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,  -- Auto-expire after 5 minutes
    confirmed_at TIMESTAMP,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'confirmed', 'expired', 'cancelled'

    -- Additional metadata
    meta_data JSONB
);

-- Indexes for pending_transactions
CREATE INDEX IF NOT EXISTS idx_pending_trans_user
ON pending_transactions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_pending_trans_code
ON pending_transactions(confirmation_code) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_pending_trans_expires
ON pending_transactions(expires_at) WHERE status = 'pending';

-- ============================================================================
-- PART 5: TELEGRAM AUTHENTICATION TOKENS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS telegram_auth_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(100) UNIQUE NOT NULL,
    telegram_chat_id BIGINT NOT NULL,

    -- Token lifecycle
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,

    -- Link details
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'used', 'expired'

    -- Security
    ip_address INET
);

-- Indexes for telegram_auth_tokens
CREATE INDEX IF NOT EXISTS idx_telegram_auth_token
ON telegram_auth_tokens(token) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_telegram_auth_chat
ON telegram_auth_tokens(telegram_chat_id, status);

-- ============================================================================
-- PART 6: AUTO-UPDATE TRIGGERS
-- ============================================================================

-- Trigger to auto-update telegram_preferences.updated_at
CREATE OR REPLACE FUNCTION update_telegram_preferences_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER telegram_preferences_update_timestamp
BEFORE UPDATE ON telegram_preferences
FOR EACH ROW
EXECUTE FUNCTION update_telegram_preferences_timestamp();

-- Trigger to auto-expire pending transactions
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
FOR EACH ROW
EXECUTE FUNCTION expire_pending_transactions();

-- ============================================================================
-- PART 7: HELPER VIEWS
-- ============================================================================

-- View for active Telegram users
CREATE OR REPLACE VIEW active_telegram_users AS
SELECT
    u.id,
    u.username,
    u.email,
    u.telegram_chat_id,
    u.telegram_username,
    u.telegram_linked_at,
    tp.language,
    tp.watchlist,
    COUNT(DISTINCT bcl.id) as command_count_30d
FROM users u
LEFT JOIN telegram_preferences tp ON u.id = tp.user_id
LEFT JOIN bot_command_log bcl ON u.id = bcl.user_id
    AND bcl.executed_at > NOW() - INTERVAL '30 days'
WHERE u.telegram_chat_id IS NOT NULL
GROUP BY u.id, tp.language, tp.watchlist;

-- View for bot command analytics
CREATE OR REPLACE VIEW bot_command_analytics AS
SELECT
    DATE(executed_at) as date,
    command,
    response_status,
    COUNT(*) as count,
    AVG(response_time_ms) as avg_response_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time_ms
FROM bot_command_log
WHERE executed_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(executed_at), command, response_status
ORDER BY date DESC, count DESC;

-- ============================================================================
-- PART 8: SAMPLE DATA (FOR TESTING)
-- ============================================================================

-- Insert default preferences for existing users (if any)
INSERT INTO telegram_preferences (user_id)
SELECT id FROM users
ON CONFLICT (user_id) DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify users table alteration
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'users' AND column_name LIKE 'telegram%';

-- Verify all tables created
-- SELECT table_name FROM information_schema.tables
-- WHERE table_name IN ('telegram_preferences', 'bot_command_log', 'pending_transactions', 'telegram_auth_tokens');

-- Verify all indexes created
-- SELECT indexname FROM pg_indexes
-- WHERE indexname LIKE '%telegram%' OR indexname LIKE '%bot_%' OR indexname LIKE '%pending_%';

-- ============================================================================
-- ROLLBACK SCRIPT (USE WITH CAUTION)
-- ============================================================================

-- DROP VIEW IF EXISTS bot_command_analytics;
-- DROP VIEW IF EXISTS active_telegram_users;
-- DROP TRIGGER IF EXISTS pending_transactions_auto_expire ON pending_transactions;
-- DROP TRIGGER IF EXISTS telegram_preferences_update_timestamp ON telegram_preferences;
-- DROP FUNCTION IF EXISTS expire_pending_transactions();
-- DROP FUNCTION IF EXISTS update_telegram_preferences_timestamp();
-- DROP TABLE IF EXISTS telegram_auth_tokens CASCADE;
-- DROP TABLE IF EXISTS pending_transactions CASCADE;
-- DROP TABLE IF EXISTS bot_command_log CASCADE;
-- DROP TABLE IF EXISTS telegram_preferences CASCADE;
-- DROP INDEX IF EXISTS idx_users_telegram_chat;
-- ALTER TABLE users DROP COLUMN IF EXISTS telegram_chat_id;
-- ALTER TABLE users DROP COLUMN IF EXISTS telegram_username;
-- ALTER TABLE users DROP COLUMN IF EXISTS telegram_linked_at;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
