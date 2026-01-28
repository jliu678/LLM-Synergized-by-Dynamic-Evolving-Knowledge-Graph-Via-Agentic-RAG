# Quick Start Guide

## 🚀 Prerequisites Check

Before starting, ensure you have:
- [ ] Python 3.11+ installed
- [ ] PostgreSQL with pgvector extension
- [ ] Neo4j database running
- [ ] 16GB RAM available
- [ ] 10GB storage space

## 📋 Step-by-Step Setup

### Step 1: Environment Setup

```bash
# Clone/Extract the project
cd kg_llm

# Create and activate virtual environment
python -m venv venv
# Windows:
. 'venv\Scripts\activate'
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup

#### PostgreSQL Setup with pgvector extension

**Windows Desktop Software**
1) Download PostgreSQL from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2) Install PostgreSQL and you will be asked to set a password for the default user `postgres`. The password will be used in the `.env` file.
3) Download and install pgvector according to https://github.com/andreiramani/pgvector_pgsql_windows/blob/main/README.md
4) Run PostgreSQL CLI:
   - when asked `Server [localhost]` press enter directly
   - when asked `database [postgres]` press enter directly: this means you have a default database named `postgres` in your PostgreSQL server
   - when asked `Port [5432]` press enter directly
   - when asked `Username [postgres]` press enter directly
   - when asked `Password for user postgres:` enter the password you set during installation
   - Run: `CREATE DATABASE sql_primekg;`
   - Run: `\c sql_primekg` to connect to the database
  - Run: `CREATE EXTENSION IF NOT EXISTS vector;`
   - Run the contents of `\i 'C:\\Users\\xxx\\kg_llm\\sql\\schema.sql'`
5) Keep the PostgreSQL running before and during you are running the project.
6) Set `DATABASE_URL` in `.env`, e.g.:
   - `DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sql_primekg` (sql_primekg is the database name)
7) verify with `python init_db.py --postgres`

**Command-line tools (if `createdb`/`psql` are on your PATH)**
```bash
# Create database
createdb primekg_rag

# Install pgvector extension
psql -d primekg_rag -c "CREATE EXTENSION vector;"

# Run schema
psql -d primekg_rag -f sql/schema.sql
```

#### Neo4j Setup
1) Download Neo4j Desktop (recommended)
2) Install and setup password for default user `neo4j`. The password will be used in the `.env` file.Default
3) Install APOC and GDS plugins in neo4j desktop app
4) record the Connection URI in .env file
5) Keep the Neo4j running before and during you are running the project
6) verify with `python init_db.py --neo4j`
```

### Step 3: Environment Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env file with your configuration:
```

Note:
The Python code uses `python-dotenv` to load `.env` at runtime.
Your shell environment (e.g., Git Bash) may still show empty values when you run `echo $LLM_BASE_URL`.
That is expected unless you explicitly export variables in your shell.

**Required .env Configuration:**
```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/sql_primekg

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# LLM Provider (choose one)
LLM_PROVIDER=openai
# Options: openai, openrouter, ollama, gemini

# LLM Configuration
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-key-here
LLM_CHOICE=gpt-4o-mini

# Embedding Configuration (recommended: local)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-m3
VECTOR_DIMENSION=1024

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8058
```

**Alternative LLM Providers:**
```env
# OpenRouter
LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-your-openrouter-key
LLM_CHOICE=anthropic/claude-3.5-sonnet

# Ollama (local)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_CHOICE=qwen2.5:14b-instruct

# Nebius
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.tokenfactory.nebius.com/v1
LLM_API_KEY=sk-your-nebius-key-here
LLM_CHOICE=meta-llama/Meta-Llama-3.1-8B-Instruct
```

### Step 4: Verify Setup

```bash
# Run the built-in verification script (loads .env automatically)
python verify_setup.py

```

### Step 5: Data Ingestion

#### Option A: Test with Small Dataset (Recommended)
```bash
# Download and ingest a small random sample (good for testing)
python ingestion/ingest.py --download --limit 100 --random-sample --verbose

# Check results
python check_neo4j_state.py

# Optional: inspect PostgreSQL content (entities/descriptions)
# python check_db.py
```

Important:
If you use `--skip-graph`, ingestion will populate PostgreSQL but Neo4j will remain at 0 nodes.

#### Option B: Full Dataset (Takes 30-60 minutes)
```bash
# Download and ingest full PrimeKG dataset
python ingestion/ingest.py --download --verbose
```

### Step 6: Start the API Server

```bash
# Start the FastAPI server
python -m agent.api

# Server runs at http://localhost:8058
# API docs available at http://localhost:8058/docs
```

### Step 7: Test the CLI

```bash
# In a new terminal
cd kg_llm
. 'venv\Scripts\activate'

# Start interactive CLI
python cli.py

# Try these test queries:
# **Disease Information**
# "What are the symptoms of Alzheimer's disease?"
# "Tell me about Type 2 diabetes"

# **Drug Queries**
# "What drugs treat hypertension?"
# "How does aspirin work?"

# **Relationship Queries**
# "What proteins are related to cancer pathways?"
# "What diseases are associated with BRCA1?"

# **Complex Queries**
# "Compare treatments for Type 1 and Type 2 diabetes"
# "Show me the relationship between EGFR and lung cancer"

```

## ✅ Daily Usage (Manual)

Run these from the project root (`kg_llm/`).

```bash
# 1) Verify environment + DB connectivity (loads .env automatically)

- Activate virtual environment:
# Windows:
. 'venv\Scripts\activate'
# Linux/Mac:
source venv/bin/activate

- establish and verity connection to PostgreSQL and neo4j
  - Keep the PostgreSQL and Neo4j running before and during you are running the project.
  - `python init_db.py --all`

- verify setup: `python verify_setup.py`

# 2) Ingest a small sample (first time) or ingest more data later
python ingestion/ingest.py --download --limit 100 --random-sample --verbose

# 3) Confirm what’s in PostgreSQL vs Neo4j
python check_neo4j_state.py

# 4) Start API (Terminal A)
python -m agent.api

# 5) Start CLI (Terminal B)
python cli.py
```

## 🧰 Script Reference (Repo Root)

- **`verify_setup.py`**
  Verifies Python/dependencies, checks `.env` exists, tests PostgreSQL + Neo4j connectivity, and checks whether `data/kg.csv` exists.

- **`init_db.py`**
  Applies PostgreSQL schema (`sql/schema.sql`) and/or tests Neo4j connection.

- **`ingestion/ingest.py`**
  PrimeKG ingestion pipeline.
  Writes:
  - PostgreSQL: entities, embeddings, relationships
  - Neo4j (Graphiti): only if you do NOT pass `--skip-graph`

- **`check_neo4j_state.py`**
  Prints Neo4j node/relationship counts and also prints PostgreSQL counts for comparison.

- **`check_db.py`**
  Quick inspection of PostgreSQL entity rows and whether descriptions exist.

- **`cli.py`**
  Interactive CLI that talks to the running API server.

- **`examples.py`**
  Programmatic examples calling the agent directly.

- **`tests/`**
  Automated tests (run with `pytest`).

Note:
`test_graph_builder.py` is a development utility for debugging Graphiti graph building.

## 🔧 Troubleshooting

### Environment Variables Not Loading
```bash
# Windows Command Prompt
set LLM_PROVIDER=openai
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_API_KEY=sk-your-key

# Windows PowerShell
$env:LLM_PROVIDER="openai"
$env:LLM_BASE_URL="https://api.openai.com/v1"
$env:LLM_API_KEY="sk-your-key"

# Linux/Mac
export LLM_PROVIDER=openai
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=sk-your-key
```


### API Not Starting
```bash
# Check if port is in use
netstat -ano | findstr :8058

# Use different port
set APP_PORT=8059
python -m agent.api
```

### Embedding Issues
```bash
# Test local embeddings
python -c "
from ingestion.embedder import Embedder
import asyncio

async def test_embedding():
    embedder = Embedder()
    result = await embedder.generate_embedding('test')
    print(f'✅ Embedding successful: {len(result)} dimensions')

asyncio.run(test_embedding())
"
```

### Graph Building Issues
```bash
# Check PostgreSQL data
python -c "
import asyncio
from agent.db_utils import get_pool

async def check_data():
    pool = await get_pool()
    async with pool.acquire() as conn:
        entities = await conn.fetchval('SELECT COUNT(*) FROM entities')
        relationships = await conn.fetchval('SELECT COUNT(*) FROM relationships')
        print(f'PostgreSQL: {entities} entities, {relationships} relationships')

asyncio.run(check_data())
"

# Check Neo4j data
python check_neo4j_state.py
```

## 📊 Expected Results

### Successful Setup Should Show:
```
✅ PostgreSQL connection successful
✅ Neo4j connection successful
✅ Embedding successful: 1024 dimensions

PostgreSQL entities: 4138
PostgreSQL embeddings: 4138
PostgreSQL relationships: 3100

Total nodes: 100+
Total relationships: 200+
```

## 🎯 Example Queries to Test

### Disease Information
- "What are the symptoms of Alzheimer's disease?"
- "Tell me about Type 2 diabetes"
- "How does cancer develop?"

### Drug Queries
- "What drugs treat hypertension?"
- "How does aspirin work?"
- "Show me medications for depression"

### Protein/Pathway Queries
- "What proteins are related to cancer pathways?"
- "Show me EGFR-related proteins"
- "Can YAP1 be a cancer treatment target?"

### Relationship Queries
- "What diseases are associated with BRCA1?"
- "Compare treatments for Type 1 and Type 2 diabetes"

## 🏗️ Project Structure

```
kg_llm/
├── agent/              # AI agent and API
│   ├── agent.py       # Main Pydantic AI agent
│   ├── api.py         # FastAPI application
│   ├── tools.py       # Agent tools (vector, graph, hybrid search)
│   ├── db_utils.py    # Database operations
│   └── graph_utils.py # Graphiti knowledge graph
├── ingestion/         # Data pipeline
│   ├── ingest.py      # Main ingestion script
│   ├── data_loader.py # PrimeKG CSV loader
│   ├── embedder.py    # Embedding generation
│   └── graph_builder.py # Neo4j graph construction
├── sql/
│   └── schema.sql     # PostgreSQL schema
├── data/              # PrimeKG CSV files
├── cli.py             # Interactive CLI interface
├── check_neo4j_state.py # Neo4j debugging tool
├── .env               # Environment configuration
└── .env.example       # Configuration template
```

## 🚀 Next Steps

1. ✅ Complete setup steps above
2. ✅ Test with small dataset (--limit 100)
3. ✅ Verify API and CLI functionality
4. ✅ Test example queries
5. ⏭️ Ingest full PrimeKG dataset
6. ⏭️ Build custom queries for your use case
7. ⏭️ Integrate with your applications

## 🆘 Support

For issues or questions:
- Check [README.md](README.md) for detailed documentation
- Verify `.env` configuration matches your setup
- Check logs for specific error messages
- Use `python check_neo4j_state.py` to debug database issues
