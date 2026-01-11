-- Initialize database with required extensions
-- This script runs automatically when the PostgreSQL container starts

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;
