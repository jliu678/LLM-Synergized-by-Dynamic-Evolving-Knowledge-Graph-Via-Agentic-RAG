-- PrimeKG Agentic RAG Database Schema
-- PostgreSQL with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables (for clean setup)
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS entity_embeddings CASCADE;
DROP TABLE IF EXISTS relationships CASCADE;
DROP TABLE IF EXISTS entities CASCADE;

-- ============================================================================
-- ENTITIES TABLE
-- Stores PrimeKG entities (diseases, drugs, proteins, pathways, etc.)
-- ============================================================================
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_index INTEGER UNIQUE NOT NULL,  -- PrimeKG node index
    node_id VARCHAR(255) NOT NULL,       -- PrimeKG node identifier
    node_name TEXT NOT NULL,             -- Entity name
    node_type VARCHAR(100) NOT NULL,     -- Entity type (disease, drug, protein, etc.)
    description TEXT,                     -- Clinical/biomedical description
    source VARCHAR(255),                  -- Data source (DrugBank, MONDO, etc.)
    metadata JSONB,                       -- Additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT entities_node_id_key UNIQUE (node_id)
);

CREATE INDEX idx_entities_node_type ON entities(node_type);
CREATE INDEX idx_entities_node_name ON entities USING gin(to_tsvector('english', node_name));
CREATE INDEX idx_entities_description ON entities USING gin(to_tsvector('english', description));
CREATE INDEX idx_entities_metadata ON entities USING gin(metadata);

-- ============================================================================
-- ENTITY EMBEDDINGS TABLE
-- Stores vector embeddings for entity descriptions
-- ============================================================================
CREATE TABLE entity_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    embedding vector(1024),  -- 1024 dimensions for BGE-M3
    embedding_model VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT entity_embeddings_entity_id_key UNIQUE (entity_id, embedding_model)
);

-- Vector similarity index (HNSW for fast approximate nearest neighbor search)
CREATE INDEX idx_entity_embeddings_vector ON entity_embeddings 
    USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- RELATIONSHIPS TABLE
-- Stores PrimeKG relationships between entities
-- ============================================================================
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type VARCHAR(255) NOT NULL,  -- Type of relationship
    display_relation VARCHAR(255),        -- Human-readable relation
    source_type VARCHAR(100),             -- Source entity type
    target_type VARCHAR(100),             -- Target entity type
    metadata JSONB,                       -- Additional relationship data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate relationships
    CONSTRAINT relationships_unique UNIQUE (source_entity_id, target_entity_id, relation_type)
);

CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relation_type);
CREATE INDEX idx_relationships_source_type ON relationships(source_type);
CREATE INDEX idx_relationships_target_type ON relationships(target_type);

-- ============================================================================
-- SESSIONS TABLE
-- Stores conversation sessions
-- ============================================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);

-- ============================================================================
-- MESSAGES TABLE
-- Stores conversation messages
-- ============================================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tool_calls JSONB,  -- Track which tools were used
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- ============================================================================
-- SEARCH FUNCTIONS
-- ============================================================================

-- Vector similarity search function
CREATE OR REPLACE FUNCTION search_entities_by_vector(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10,
    filter_type VARCHAR(100) DEFAULT NULL
)
RETURNS TABLE (
    entity_id UUID,
    node_name TEXT,
    node_type VARCHAR(100),
    description TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.node_name,
        e.node_type,
        e.description,
        1 - (ee.embedding <=> query_embedding) as similarity
    FROM entity_embeddings ee
    JOIN entities e ON e.id = ee.entity_id
    WHERE 
        1 - (ee.embedding <=> query_embedding) > match_threshold
        AND (filter_type IS NULL OR e.node_type = filter_type)
    ORDER BY ee.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Hybrid search function (vector + keyword)
CREATE OR REPLACE FUNCTION search_entities_hybrid(
    query_embedding vector(1024),
    query_text TEXT,
    match_count int DEFAULT 10,
    vector_weight float DEFAULT 0.7,
    filter_type VARCHAR(100) DEFAULT NULL
)
RETURNS TABLE (
    entity_id UUID,
    node_name TEXT,
    node_type VARCHAR(100),
    description TEXT,
    combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.node_name,
        e.node_type,
        e.description,
        (
            vector_weight * (1 - (ee.embedding <=> query_embedding)) +
            (1 - vector_weight) * ts_rank(
                to_tsvector('english', COALESCE(e.description, '') || ' ' || e.node_name),
                plainto_tsquery('english', query_text)
            )
        ) as combined_score
    FROM entity_embeddings ee
    JOIN entities e ON e.id = ee.entity_id
    WHERE 
        (filter_type IS NULL OR e.node_type = filter_type)
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- Get entity relationships
CREATE OR REPLACE FUNCTION get_entity_relationships(
    entity_node_id VARCHAR(255),
    max_depth int DEFAULT 1
)
RETURNS TABLE (
    source_name TEXT,
    relation_type VARCHAR(255),
    target_name TEXT,
    source_type VARCHAR(100),
    target_type VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e1.node_name as source_name,
        r.relation_type,
        e2.node_name as target_name,
        e1.node_type as source_type,
        e2.node_type as target_type
    FROM relationships r
    JOIN entities e1 ON r.source_entity_id = e1.id
    JOIN entities e2 ON r.target_entity_id = e2.id
    WHERE e1.node_id = entity_node_id OR e2.node_id = entity_node_id
    ORDER BY r.relation_type;
END;
$$;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to entities and sessions
CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE entities IS 'PrimeKG biomedical entities (diseases, drugs, proteins, etc.)';
COMMENT ON TABLE entity_embeddings IS 'Vector embeddings for entity descriptions';
COMMENT ON TABLE relationships IS 'PrimeKG relationships between entities';
COMMENT ON TABLE sessions IS 'User conversation sessions';
COMMENT ON TABLE messages IS 'Conversation messages with tool usage tracking';

-- ============================================================================
-- INITIAL STATS
-- ============================================================================

-- Display table information
SELECT 
    'Schema created successfully!' as status,
    'Remember to adjust vector dimension in entity_embeddings table based on your embedding model' as note;
