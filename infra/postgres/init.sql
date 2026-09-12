-- ULTRONE PostgreSQL initialization
-- This script runs on first container start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY DEFAULT 'entity_' || replace(uuid_generate_v4()::text, '-', ''),
    type TEXT NOT NULL DEFAULT 'unknown',
    status TEXT NOT NULL DEFAULT 'unknown',
    confidence REAL NOT NULL DEFAULT 0.0,
    position JSONB,
    velocity JSONB,
    sensors JSONB DEFAULT '[]',
    observations JSONB DEFAULT '[]',
    relationships JSONB DEFAULT '[]',
    provenance JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY DEFAULT 'evt_' || replace(uuid_generate_v4()::text, '-', ''),
    type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT,
    entity_id TEXT REFERENCES entities(entity_id),
    changes JSONB DEFAULT '{}',
    confidence REAL DEFAULT 1.0,
    provenance JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Decisions audit table
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY DEFAULT 'dec_' || replace(uuid_generate_v4()::text, '-', ''),
    type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT,
    model TEXT,
    reasoning TEXT,
    confidence REAL DEFAULT 1.0,
    alternatives JSONB DEFAULT '[]',
    provenance JSONB DEFAULT '[]',
    human_approval TEXT, -- 'approved', 'rejected', 'pending'
    outcome TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_entity_id ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp);
