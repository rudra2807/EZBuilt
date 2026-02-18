-- Initial schema for EZBuilt
-- Run this migration on your Aurora PostgreSQL instance

-- Enable UUID extension (for aws_integrations.id only)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (user_id is Cognito sub, not auto-generated)
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,  -- Cognito sub attribute
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- AWS Integration status enum
CREATE TYPE integration_status AS ENUM ('pending', 'connected', 'failed');

-- AWS Integrations table
CREATE TABLE aws_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    aws_account_id VARCHAR(12),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    role_arn VARCHAR(255),
    status integration_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Indexes for performance
CREATE INDEX idx_aws_integrations_user_id ON aws_integrations(user_id);
CREATE INDEX idx_aws_integrations_external_id ON aws_integrations(external_id);
CREATE INDEX idx_aws_integrations_status ON aws_integrations(status);
CREATE INDEX idx_users_email ON users(email);

-- Comments for documentation
COMMENT ON TABLE users IS 'User accounts for EZBuilt platform';
COMMENT ON COLUMN users.user_id IS 'Cognito sub attribute (unique user identifier from AWS Cognito)';
COMMENT ON TABLE aws_integrations IS 'AWS account connections via cross-account roles';
COMMENT ON COLUMN aws_integrations.external_id IS 'Unique identifier for secure role assumption';
COMMENT ON COLUMN aws_integrations.verified_at IS 'Timestamp when role assumption was successfully verified';
