-- Create the TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

---
-- TABLE 1: agents
-- Holds static info and hierarchy (College/Lab)
---
CREATE TABLE agents (
    agent_id UUID PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    
    -- Hierarchy Columns (for your College/Lab analogy)
    -- These can be NULL if not used
    group_name VARCHAR(255),  -- e.g., "CSE Department"
    sub_group_name VARCHAR(255), -- e.g., "Lab 1"
    
    -- Other static info
    os VARCHAR(255),
    cpu_cores_physical INT,
    cpu_cores_logical INT,
    ram_total_gb NUMERIC(10, 2),
    
    -- Status tracking
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ,
    
    -- Store partitions as JSONB for flexibility
    partitions JSONB
);

---
-- TABLE 2: metrics_high_freq
-- This is the main time-series table
---
CREATE TABLE metrics_high_freq (
    "timestamp" TIMESTAMPTZ NOT NULL,
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Core metrics
    cpu_percent_overall FLOAT,
    ram_percent_used FLOAT,
    swap_percent_used FLOAT,
    
    -- I/O metrics
    disk_read_bytes_per_sec BIGINT,
    disk_write_bytes_per_sec BIGINT,
    net_bytes_sent_per_sec BIGINT,
    net_bytes_recv_per_sec BIGINT
);

-- Turn it into a TimescaleDB Hypertable
SELECT create_hypertable('metrics_high_freq', 'timestamp');

---
-- TABLE 3: metrics_low_freq (Disk Usage)
-- This is a separate time-series table
---
CREATE TABLE metrics_low_freq_disk (
    "timestamp" TIMESTAMPTZ NOT NULL,
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Disk info
    mountpoint VARCHAR(255),
    percent_used FLOAT,
    total_gb NUMERIC(10, 2),
    used_gb NUMERIC(10, 2),

    -- Make a unique key so we can UPSERT
    PRIMARY KEY (agent_id, mountpoint, "timestamp")
);

-- Turn it into a TimescaleDB Hypertable
SELECT create_hypertable('metrics_low_freq_disk', 'timestamp');

---
-- TABLE 4: process_data
-- Stores top processes (only sent on threshold breach)
---
CREATE TABLE metrics_processes (
    "timestamp" TIMESTAMPTZ NOT NULL,
    agent_id UUID NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    
    -- Process info
    pid INT,
    name VARCHAR(255),
    username VARCHAR(255),
    cpu_percent FLOAT,
    memory_percent FLOAT
);

-- Turn it into a TimescaleDB Hypertable
SELECT create_hypertable('metrics_processes', 'timestamp');