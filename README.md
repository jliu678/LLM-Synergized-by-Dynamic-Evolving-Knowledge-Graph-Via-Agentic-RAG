# Temporal Domain Expertise in Synergy with LLM's World Knowledge: Agentic RAG with Dynamic Evolving Knowledge Graph Based on PrimeKG

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A production-ready biomedical knowledge retrieval system that combines **PrimeKG** (Precision Medicine Knowledge Graph) with **Graphiti** for intelligent, context-aware medical information queries. Uses Pydantic AI agents with dual search modes to intelligently traverse both vector embeddings and graph relationships for comprehensive biomedical insights.

## 🎯 Overview

Traditional RAG systems rely solely on vector similarity, missing crucial relationship context in biomedical domains. This system bridges that gap by:

- **Combining two complementary search paradigms**: Dense vector search for semantic relevance + Graph traversal for explicit relationships
- **Leveraging PrimeKG's rich biomedical data**: 129K+ entities and 4M+ relationships across diseases, drugs, proteins, and pathways
- **Enabling temporal reasoning**: Dynamic knowledge graph management through Graphiti for evolving medical knowledge
- **Providing flexible LLM support**: Seamlessly switch between OpenAI, Ollama, OpenRouter, and Gemini

## ✨ Key Features

### 🔍 Dual Search Architecture
- **Vector Search**: Fast semantic similarity matching over clinical descriptions using pgvector
- **Graph Search**: Relationship-aware traversal for discovering indirect connections and multi-hop pathways
- **Hybrid Search**: Intelligently combines both methods for comprehensive results

### 📊 Rich Knowledge Base
- **PrimeKG Integration**: Pre-built precision medicine knowledge graph with 129K+ biomedical entities
- **4M+ Relationships**: Comprehensive coverage of drug-disease, protein-pathway, gene-phenotype associations
- **Multiple Entity Types**: Diseases, drugs, proteins, pathways, side effects, and more

### 🧠 Intelligent Agent Design
- **Pydantic AI Agents**: Type-safe, composable AI agent framework with structured outputs
- **Multi-tool Reasoning**: Agents autonomously decide which search mode(s) to use based on query intent
- **Error Recovery**: Graceful fallbacks and retry logic for robust operation

### 🚀 Production Ready, Always Improvable
- **FastAPI Backend**: High-performance async API with automatic OpenAPI documentation
- **Streaming Responses**: Real-time answer streaming for better UX
- **Comprehensive Error Handling**: Detailed error messages and logging
- **Database Abstraction**: PostgreSQL with pgvector for embeddings, Neo4j for graph storage

### 🔧 Flexible Configuration
- **Multiple LLM Providers**: OpenAI, Ollama (local), OpenRouter, Google Gemini
- **Pluggable Embeddings**: Support for different embedding models
- **Configurable Search Parameters**: Fine-tune search behavior per deployment

## 🏗️ Architecture


### Data Flow Architecture

```
Input Query
    │
    ▼
┌─────────────────────────────────┐
│  Intent Recognition & Planning  │
│  (What search modes needed?)    │
└──────┬──────────────────────────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Vector Search       │    │  Graph Search        │
│                      │    │                      │
│ 1. Embed query       │    │ 1. Parse entities    │
│ 2. Find similar      │    │ 2. Traverse graph    │
│    entities          │    │ 3. Extract paths    │
│ 3. Retrieve context  │    │ 4. Score results    │
└──────┬───────────────┘    └──────┬──────────────┘
       │                           │
       └───────────────┬───────────┘
                       ▼
            ┌────────────────────────┐
            │  Result Fusion         │
            │  (Deduplicate & Rank)  │
            └───────────┬────────────┘
                        ▼
            ┌────────────────────────┐
            │  LLM Answer Generation │
            │  (Streaming Output)    │
            └────────────┬───────────┘
                         ▼
                    User Response
```

### Key Architectural Advantages

#### 1️⃣ **Reduced Hallucination**
- Graph structure provides grounded facts and explicit relationships
- Vector search validates semantic similarity with factual verification
- LLM acts as synthesizer rather than source of knowledge

#### 2️⃣ **Context-Aware Reasoning**
- Discovers multi-hop relationships (e.g., "What pathways connect this gene to the disease?")
- Understands entity types and relationship semantics
- Handles complex biomedical questions requiring relationship reasoning

#### 3️⃣ **Scalability & Efficiency**
- **Vector Search**: O(log n) retrieval with pgvector indexing
- **Graph Search**: Efficient relationship lookup with Neo4j
- **Hybrid Approach**: Falls back gracefully when one method is insufficient
- Caching layer reduces redundant computations

#### 4️⃣ **Transparency & Interpretability**
- Search results include explicit relationship paths
- Users see exactly which entities and relationships informed the answer
- Audit trail for compliance in clinical settings

#### 5️⃣ **Extensibility**
- Modular design allows easy addition of new data sources
- Pluggable LLM providers support latest models
- Temporal knowledge graph enables version tracking and historical queries
- Custom tools can be added to agent framework

## 📋 Project Structure

```
kg_llm/
├── agent/                    # AI Agent & API Layer
│   ├── agent.py             # Pydantic AI agent with tools
│   ├── api.py               # FastAPI application & endpoints
│   ├── tools.py             # Tool definitions for agent
│   ├── db_utils.py          # PostgreSQL & pgvector utilities
│   ├── graph_utils.py       # Graphiti & Neo4j integration
│   ├── models.py            # Pydantic data models
│   ├── providers.py         # LLM provider abstraction layer
│   └── prompts.py           # System prompts & instructions
│
├── ingestion/               # Data Pipeline Layer
│   ├── ingest.py            # Main ingestion pipeline
│   ├── data_loader.py       # PrimeKG CSV parser
│   ├── embedder.py          # Embedding generation & storage
│   └── graph_builder.py     # Graphiti graph construction
│
├── sql/                     # Database Schemas
│   └── schema.sql           # PostgreSQL schema with pgvector
│
├── data/                    # Knowledge Base (Downloaded)
│   ├── disease_*.csv
│   ├── drug_*.csv
│   ├── protein_*.csv
│   └── ...
│
├── cli.py                   # Interactive CLI interface
├── .env.example             # Configuration template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🎬 Real-World Q&A Demonstration

Below are actual conversations demonstrating the system's ability to answer complex biomedical questions by **combining knowledge from PrimeKG with the LLM's reasoning capabilities**. Each example shows:

- **[PrimeKG]** = Factual data retrieved from the precision medicine knowledge graph
- **[LLM]** = Reasoning, synthesis, or general biomedical knowledge from the language model
- **[HYBRID]** = Integration of both sources for comprehensive answers

#### Example 1: Cancer Prevention Overview
```
User: "What is cancer, is it preventable?"

Agent Response (annotated with knowledge sources):

[HYBRID] Cancer is classified as a disease—a condition in which cells acquire 
the ability to divide without normal regulatory controls, evade apoptosis, and 
often acquire capabilities such as tissue invasion and metastasis.
  └─ [PrimeKG] Cancer classification as disease entity
  └─ [LLM] Cellular mechanisms of transformation (synthesis)

Prevention spans multiple levels:
┌─────────────────────────────────────────────────────────────┐
│ Primary Prevention                                          │
├─────────────────────────────────────────────────────────────┤
│ [LLM] • Tobacco cessation – eliminates exposure to          │
│        carcinogens for lung, head-neck, bladder,            │
│        pancreatic cancers                                   │
│ [LLM] • Limited alcohol – reduces oral, esophageal, liver, │
│        breast, colorectal cancer risk                       │
│ [HYBRID] • Vaccination – HBV prevents hepatocellular        │
│          carcinoma; HPV prevents cervical and               │
│          oropharyngeal cancers                              │
│          └─ [PrimeKG] Specific disease-vaccine links        │
│ [LLM] • Healthy diet & weight control – reduces colorectal,│
│        breast, endometrial, pancreatic cancer risk          │
│ [LLM] • Physical activity – reduces breast, colon,          │
│        endometrial cancer risk                              │
│ [LLM] • UV protection – limits skin cancer risk             │
└─────────────────────────────────────────────────────────────┘

[LLM] Secondary Prevention:
Screening programs (colonoscopy, mammography, Pap testing) 
detect pre-malignant or early-stage disease, enabling curative treatment.

[HYBRID] Key Point: While inherited mutations (BRCA1/2, Lynch syndrome) 
can be unavoidable, a large proportion of cancers can be prevented 
through lifestyle choices, vaccination, and screening.
  └─ [PrimeKG] BRCA1/2, Lynch syndrome entities in KG
  └─ [LLM] Synthesis of preventability concept

Knowledge Source Summary:
✓ PrimeKG provided: Disease classification, vaccine-disease links
✓ LLM provided: General prevention knowledge, epidemiological context
```

#### Example 2: Knowledge Graph Coverage Assessment
```
User: "Does PrimeKG have cancer prevention information?"

Agent Response (annotated):

[HYBRID - Self-Assessment] PrimeKG contains relevant biomedical information 
but lacks a dedicated "cancer-prevention" node with comprehensive preventive measures.
  └─ [Agent] Directly queried PrimeKG vector/graph search
  └─ [LLM] Interpreted search results to assess gaps

What PrimeKG DOES contain (verified by direct query):
[PrimeKG-Verified] ✓ Individual drug entities (Aspirin, Tamoxifen, Metformin)
[PrimeKG-Verified] ✓ Disease-specific cancer types (oropharynx cancer, etc.)
[PrimeKG-Verified] ✓ Molecular pathways and biological processes
[PrimeKG-Verified] ✓ Drug-to-disease relationships

What needs assembly (LLM synthesis):
[LLM-Required] → Query drug entities individually (aspirin, tamoxifen, metformin)
[LLM-Required] → Extract drug-disease relationships
[LLM-Required] → Infer preventive context from relationships

Example: Querying "Aspirin" (from PrimeKG):
[PrimeKG] - Drug: Aspirin
[PrimeKG] - Target: COX-1/COX-2 (Cycloxygenase inhibition)
[PrimeKG] - Associated diseases: Colorectal, esophageal, breast cancers
[LLM]     → This can be connected to colorectal cancer prevention evidence

[LLM] Practical approach: Combine vector search (semantics) + graph 
traversal (relationships) to piece together prevention strategies 
from scattered KG entries.

Knowledge Source Summary:
✓ PrimeKG verified: Drug entities, disease nodes, relationship coverage
✓ LLM contributed: Gap analysis, assembly strategy, interpretability
✗ PrimeKG gap: No explicit "prevents cancer" relationships (requires inference)
```

#### Example 3: Chemoprevention Drug Analysis
```
User: "Get cancer prevention strategies indicated by PrimeKG 
and evaluate them"

Agent Response (annotated):

╔════════════════════════════════════════════════════════════════╗
║          CHEMOPREVENTION AGENTS IN PrimeKG                    ║
║               (Knowledge Source Attribution)                  ║
╚════════════════════════════════════════════════════════════════╝

┌──────────┬──────────────────┬──────────────────┬──────────────┐
│ Drug     │ Cancer Type(s)   │ Target           │ Evidence     │
│          │                  │ [PrimeKG Extract]│ Strength     │
├──────────┼──────────────────┼──────────────────┼──────────────┤
│ Aspirin  │ [PrimeKG]        │ [PrimeKG]        │ ✓ [LLM]      │
│          │ Colorectal,      │ COX-1/COX-2      │ High (multi- │
│          │ Breast, Prostate │ inhibition       │ trial data)  │
├──────────┼──────────────────┼──────────────────┼──────────────┤
│Tamoxifen │ [PrimeKG]        │ [PrimeKG]        │ ✓ [LLM]      │
│          │ ER+ Breast       │ Estrogen         │ High (RCTs)  │
│          │ (high-risk)      │ Receptor-α       │              │
├──────────┼──────────────────┼──────────────────┼──────────────┤
│Metformin │ [PrimeKG]        │ [PrimeKG]        │ ✗ [LLM]      │
│          │ Colorectal,      │ AMPK activation  │ Single-study │
│          │ Breast,          │                  │ (mechanistic)│
│          │ Endometrial      │                  │              │
├──────────┼──────────────────┼──────────────────┼──────────────┤
│Finasteride│ [PrimeKG]       │ [PrimeKG]        │ ✓ [LLM]      │
│          │ Prostate         │ 5α-Reductase     │ PCPT trial   │
│          │ (low-grade)      │ inhibition       │ evidence     │
├──────────┼──────────────────┼──────────────────┼──────────────┤
│ Statins  │ [PrimeKG]        │ [PrimeKG]        │ ✗ [LLM]      │
│          │ Colorectal,      │ HMG-CoA          │ Mixed        │
│          │ Breast (mixed)   │ reductase        │ evidence     │
└──────────┴──────────────────┴──────────────────┴──────────────┘

Key Findings (Generated via System Reasoning):
[LLM] → Aspirin, tamoxifen show strongest curated evidence (✓)
[LLM] → Metformin, statins have promising but limited KG coverage (✗)
[PrimeKG] → Each drug has documented molecular target and cancer association
[LLM] → Benefit-risk profiles must be weighed against individual factors

Clinical Recommendation (Synthesized from both):
[PrimeKG + LLM] Aspirin: Consider for adults ≥50 with cardiovascular risk
[PrimeKG + LLM] Tamoxifen: For high-risk breast cancer women (BRCA-negative)
[PrimeKG + LLM] Metformin: Overweight/diabetic patients with elevated risk
[PrimeKG + LLM] Finasteride: Men with elevated PSA, low high-grade disease risk

Evaluation Methodology:
1. [Agent] Queried PrimeKG vector/graph search for "chemoprevention"
2. [Agent] Extracted drug, cancer type, and target relationships
3. [LLM] Graded evidence strength based on clinical trial annotation
4. [LLM] Synthesized benefit-risk profiles from domain knowledge
5. [HYBRID] Created actionable recommendations combining both

Knowledge Source Summary:
✓ PrimeKG provided: 10 drugs with cancer associations and molecular targets
✓ LLM provided: Evidence grading, clinical context, synthesis, recommendations
```

#### Example 4: Drug Interaction Analysis
```
User: "What's the interaction between propranolol and statins?"

Agent Response (annotated):

╔════════════════════════════════════════════════════════════════╗
║         PROPRANOLOL + STATINS INTERACTION PROFILE             ║
║              (Knowledge Source Attribution)                   ║
╚════════════════════════════════════════════════════════════════╝

Pharmacokinetic Interaction: MINIMAL ✓
├─ [PrimeKG] Propranolol metabolized by: CYP2D6
├─ [PrimeKG] Statins metabolized by: CYP3A4, CYP2C9, CYP2C19 (varies)
└─ [LLM-Synthesized] Conclusion: Separate enzyme pathways = low PK 
                     interaction risk

Pharmacodynamic Interactions: MONITOR ⚠️
├─ [LLM] Additive hypotension: β-blockade + statin-induced BP reduction
├─ [LLM] Glucose effects: Both may worsen glycemic control
│  (β-blocker ↑ insulin resistance + statin ↑ fasting glucose)
├─ [LLM] Myopathy overlap: Both cause muscle-related side effects
│  (makes differentiation difficult)
└─ [LLM] Lipid profile: Non-vasodilating β-blockers may ↑ TG, ↓ HDL

Clinical Evidence (from LLM domain knowledge):
[LLM] ✓ Meta-analyses show the combination is SAFE
[LLM] ✓ Standard of care for post-MI and CAD patients
[LLM] ✓ Outcome studies support dual use without excess adverse events

Prescribing Recommendations (LLM clinical reasoning):
┌─────────────────────────────────────┬──────────────────────────┐
│ Patient Type                        │ Action (LLM-Generated)   │
├─────────────────────────────────────┼──────────────────────────┤
│ New to both drugs                   │ Start low doses, titrate │
│                                     │ gradually, monitor BP/HR │
├─────────────────────────────────────┼──────────────────────────┤
│ Elderly/volume-depleted             │ Reduce propranolol       │
│                                     │ initial dose (5mg BID)   │
├─────────────────────────────────────┼──────────────────────────┤
│ Diabetic                            │ Check HbA1c at 3 months, │
│                                     │ adjust antidiabetics     │
├─────────────────────────────────────┼──────────────────────────┤
│ Develops myalgia                    │ Hold statin, check CK,   │
│                                     │ switch to lower-risk drug│
└─────────────────────────────────────┴──────────────────────────┘

[LLM] Bottom Line: Safe combination when properly monitored. Watch for 
orthostatic hypotension in elderly, glycemic changes in diabetics, 
and muscle symptoms in all patients.

Knowledge Source Summary:
✓ PrimeKG provided: Drug metabolic pathways (CYP enzymes)
✓ LLM provided: Pharmacodynamic reasoning, clinical evidence synthesis, 
                 personalized prescribing recommendations
✗ PrimeKG gap: No explicit drug-drug interaction node (requires LLM reasoning)

Why Hybrid Approach Works Here:
1. PrimeKG gives precise enzymatic pathways
2. LLM integrates multiple pharmacologic concepts for interaction prediction
3. LLM supplies clinical context and outcome data not in structured KG
4. Combined approach enables reasoning beyond what either could alone
```

---

### Knowledge Source Analysis

The Q&A examples above demonstrate how the **Agentic RAG system intelligently combines two distinct knowledge sources**:

#### What PrimeKG Provides (Structured Biomedical Facts)
| Data Type | Examples | Use Case |
|-----------|----------|----------|
| **Entity Information** | Disease definitions, drug names, protein identifiers | Grounding queries in real biomedical entities |
| **Relationships** | Drug-disease associations, protein-pathway links | Discovering direct connections and multi-hop paths |
| **Molecular Targets** | CYP450 enzymes, estrogen receptors, kinase targets | Understanding drug mechanisms |
| **Graph Structure** | Disease-to-disease similarity, drug-to-protein binding | Inferring related conditions and alternative therapies |

**Limitations of PrimeKG alone:**
- ✗ No reasoning capability (can't synthesize across domains)
- ✗ Sparse coverage on preventive relationships
- ✗ No access to recent clinical trial data
- ✗ Cannot explain "why" beyond stated relationships
- ✗ Limited to entities explicitly present in the graph

#### What the LLM Provides (Reasoning & Synthesis)
| Capability | Examples | Value |
|-----------|----------|-------|
| **Clinical Reasoning** | Connecting enzyme pathways to drug interactions | Predicting effects not explicitly in KG |
| **Evidence Synthesis** | Integrating multiple studies into recommendations | Assessing overall strength of evidence |
| **Context & Nuance** | Explaining preventability despite genetic factors | Adding clinical wisdom and caveats |
| **Personalization** | Tailoring recommendations to patient risk factors | Making generic knowledge patient-specific |
| **Explanation** | Describing mechanisms and rationales | Improving clinician understanding |

**Limitations of LLM alone:**
- ✗ May hallucinate non-existent drugs or relationships
- ✗ Knowledge cutoff limits recent advances
- ✗ No structured verification against biomedical facts
- ✗ Can't guarantee accuracy of complex drug interactions

#### Hybrid Approach Advantages (The Key Insight)

| Scenario | LLM Alone | PrimeKG Alone | Hybrid System |
|----------|-----------|---------------|---------------|
| **Q: What drugs treat cancer?** | Generates plausible list, may include made-up drugs | Returns exact entities in KG (limited scope) | ✓ Returns verified drugs + clinical context |
| **Q: Why does aspirin prevent colorectal cancer?** | Explains mechanism but may be inaccurate | No explanation (just relationship node) | ✓ Verified target (COX-1/COX-2) + mechanistic explanation |
| **Q: Propranolol + statin interaction?** | Good reasoning but unverified | Lists separate drug nodes, no interaction analysis | ✓ Cross-references PrimeKG pathways + synthesizes interaction risk |
| **Q: Is drug X in PrimeKG?** | Uncertain (may confabulate) | Definitive answer via graph query | ✓ Agent knows exactly what's in KG after querying |

**Example: Example 2 (KG Coverage Assessment) is the Most Revealing**

This example shows the system **introspecting on its own knowledge**: 
- The agent doesn't assume PrimeKG has prevention information
- It **queries PrimeKG directly** to find what's actually there
- The LLM **interprets the search results** to identify gaps
- The response acknowledges both what exists and what's missing

This prevents hallucination because:
1. ✓ PrimeKG search results are grounded facts
2. ✓ LLM only interprets those facts, not inventing data
3. ✓ Agent explicitly states what requires inference vs. what is verified

#### Agent Workflow (How Both Sources Are Used)

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│ LLM: Understand intent & plan searches  │
└─────────────┬───────────────────────────┘
              │
              ├─► [PrimeKG] Vector search on entity descriptions
              │                    ↓
              │           [LLM] Interpret semantic results
              │
              ├─► [PrimeKG] Graph traversal for relationships
              │                    ↓
              │           [LLM] Score and rank paths
              │
              └─► [PrimeKG] Entity relationship lookups
                             ↓
                  [LLM] Verify molecular targets, pathways
                             │
                             ▼
              ┌────────────────────────────────┐
              │ [LLM] Synthesis & Reasoning    │
              │ • Integrate PrimeKG findings  │
              │ • Add clinical context        │
              │ • Generate recommendations    │
              │ • Flag uncertainties          │
              └────────────────────────────────┘
                             │
                             ▼
                      User Response
                  (Facts grounded in PrimeKG,
                  Reasoning enhanced by LLM)
```

#### Key Design Decisions

1. **Always Query PrimeKG First**: The agent doesn't rely on LLM's training data alone
2. **Transparent About Gaps**: Explicitly states what PrimeKG lacks (Example 2)
3. **LLM for Synthesis Only**: Reasoning combines PrimeKG facts, not replaces them
4. **Evidence Grading**: Shows confidence levels (✓ vs ✗) based on KG coverage
5. **Fallback Strategy**: If PrimeKG doesn't have data, LLM explains why and what's missing

---

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (with pgvector extension)
- Neo4j 5.0+ (or use Neo4j AuraDB)
- API keys for your chosen LLM provider


### Installation & Configuration

See [Instructions.md](./Instructions.md) for detailed setup instructions including:
- Database initialization
- PrimeKG data download & ingestion
- LLM provider configuration
- Embedding model selection
- Graphiti temporal KG setup

## 💬 Example Queries

### 🏥 Disease Information
Retrieve comprehensive clinical details about medical conditions:
```
"What are the main symptoms of Alzheimer's disease?"
"Tell me about the pathophysiology of Type 2 diabetes"
"Which organs are affected by polycystic kidney disease?"
```

### 💊 Drug & Treatment Queries
Explore pharmacological interventions and mechanisms:
```
"What drugs are approved for treating hypertension?"
"How does aspirin work as an anticoagulant?"
"What are the side effects of metformin?"
"Which drugs interact with warfarin?"
```

### 🧬 Biological Relationships
Discover connections between genes, proteins, and clinical outcomes:
```
"What proteins are involved in cancer cell proliferation pathways?"
"What diseases are associated with mutations in BRCA1?"
"Which genes are upregulated in response to inflammation?"
"What pathways does TNF-alpha participate in?"
```

### ⚖️ Complex Multi-step Analysis
Investigate sophisticated biomedical questions requiring relationship reasoning:
```
"Compare the molecular mechanisms of Type 1 and Type 2 diabetes treatment"
"Show me the complete pathway from EGFR mutation to lung cancer development"
"What is the relationship between APOE4 genotype and Alzheimer's disease risk?"
"Which therapeutic targets are common between Parkinson's and Alzheimer's disease?"
```

### 📊 Query Categories Reference

| Category | Intent | Example |
|:---------|:-------|:--------|
| **Symptoms & Manifestations** | Clinical diagnosis & patient education | "What are the early warning signs of heart disease?" |
| **Mechanisms & Pharmacology** | Understanding drug action & biological processes | "How does metformin improve insulin sensitivity?" |
| **Relationship Discovery** | Finding associations between entities | "What diseases are linked to high cholesterol?" |
| **Pathway Analysis** | Mapping biological networks | "What genes are involved in the apoptosis pathway?" |
| **Comparative Analysis** | Contrasting conditions, treatments, or mechanisms | "What's the difference between bacterial and viral pneumonia?" |

## 🔧 Configuration Options

### Environment Variables
```bash
# LLM Provider (choose one)
LLM_PROVIDER=openai              # Options: openai, ollama, openrouter, gemini
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# Database
POSTGRES_URL=postgresql://user:pass@localhost/kg_llm
NEO4J_URL=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Search Parameters
VECTOR_SEARCH_TOP_K=10           # Number of vector results
GRAPH_SEARCH_MAX_DEPTH=3         # Graph traversal depth
HYBRID_SEARCH_FUSION_METHOD=rrf  # Reciprocal Rank Fusion

# Graphiti Settings
GRAPHITI_ENABLED=true
GRAPHITI_TEMPORAL_GRANULARITY=day
```

See `.env.example` for all available configuration options.


## 🛠️ API Endpoints

```bash
# Query the agent
POST /api/v1/query
{
  "query": "What are the risk factors for Type 2 diabetes?",
  "search_mode": "hybrid",  # vector, graph, or hybrid
  "stream": true
}

# Get entity details
GET /api/v1/entities/{entity_id}

# Search vector space
POST /api/v1/search/vector
{
  "query": "insulin resistance",
  "top_k": 10
}

# Traverse graph
POST /api/v1/search/graph
{
  "entity_id": "disease_12345",
  "relationship_type": "treats",
  "max_depth": 2
}

# Health check
GET /api/v1/health
```

See FastAPI docs at `http://localhost:8000/docs` for interactive API exploration.



## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Support & Questions

- 📖 **Documentation**: See [Instructions.md](./Instructions.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/kg_llm/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/kg_llm/discussions)

## 🙏 Acknowledgments

- **PrimeKG**: Precision Medicine Knowledge Graph by Arjun Delivoria et al.
- **Graphiti**: Temporal knowledge graph framework
- **Pydantic AI**: Type-safe AI agent framework
- **FastAPI**: Modern, fast web framework for building APIs