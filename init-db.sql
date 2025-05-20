-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the lua_chunks table if it doesn't exist
CREATE TABLE IF NOT EXISTS lua_chunks (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    content TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    meta_data JSONB,
    embedding VECTOR(384)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_lua_chunks_file_path ON lua_chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_lua_chunks_chunk_type ON lua_chunks(chunk_type);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dcs_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dcs_user;