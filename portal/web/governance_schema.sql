-- Governance Database Schema
-- This file contains the database schema for the governance/engagement system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    motion_id VARCHAR(255) NOT NULL,
    author_id VARCHAR(255) NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Votes table (up/down votes)
CREATE TABLE IF NOT EXISTS votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    motion_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (motion_id, user_id)
);

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    interacted_motion_ids JSONB DEFAULT '[]'::jsonb,
    preferred_statuses JSONB DEFAULT '{}'::jsonb,
    total_interactions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- View tracking table (for analytics)
CREATE TABLE IF NOT EXISTS motion_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    motion_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_comments_motion_id ON comments(motion_id);
CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);
CREATE INDEX IF NOT EXISTS idx_comments_motion_created ON comments(motion_id, created_at);
CREATE INDEX IF NOT EXISTS idx_votes_motion_id ON votes(motion_id);
CREATE INDEX IF NOT EXISTS idx_votes_user_id ON votes(user_id);
CREATE INDEX IF NOT EXISTS idx_votes_motion_direction ON votes(motion_id, direction);
CREATE INDEX IF NOT EXISTS idx_motion_views_motion_id ON motion_views(motion_id);
CREATE INDEX IF NOT EXISTS idx_motion_views_user_id ON motion_views(user_id);
CREATE INDEX IF NOT EXISTS idx_motion_views_viewed_at ON motion_views(viewed_at);
CREATE INDEX IF NOT EXISTS idx_motion_views_motion_user ON motion_views(motion_id, user_id);