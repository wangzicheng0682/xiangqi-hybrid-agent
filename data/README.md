# Data Directory Structure

This directory contains all external resources needed for the Xiangqi Hybrid Agent system.

## Directory Layout

```
data/
├── engine/           # Chess engine binaries
│   └── pikafish      # Pikafish executable (Linux/Mac)
│   └── pikafish.exe  # Pikafish executable (Windows)
│
├── books/            # Chess book PDFs for RAG retrieval
│   ├── 橘中秘.pdf
│   ├── 梅花谱.pdf
│   └── ...
│
├── games/            # Historical game records (PGN format)
│   ├── professional_games.pgn
│   └── ...
│
├── vector_db/        # FAISS vector database indices
│   ├── books.index   # Book content embeddings
│   └── books.meta    # Book metadata
│
└── graph_db/         # Neo4j graph database files
    └── (Neo4j managed)
```

## Resource Preparation (Sprint 2.1)

### 1. Pikafish Engine

**Download:**
- Official releases: https://github.com/official-pikafish/Pikafish/releases
- Choose the appropriate version for your platform:
  - Linux: `pikafish-bmi2-linux.tar.bz2` (modern CPUs) or `pikafish-modern-linux.tar.bz2`
  - macOS: `pikafish-bmi2-apple.tar.bz2` (Apple Silicon) or `pikafish-modern-mac.tar.bz2`
  - Windows: `pikafish-bmi2-win.zip` or `pikafish-modern-win.zip`

**Installation:**
```bash
# Linux/Mac
cd data/engine
tar -xjf pikafish-bmi2-linux.tar.bz2
chmod +x pikafish

# Windows: Extract to data\engine\pikafish.exe
```

**Verification:**
```bash
./data/engine/pikafish
# Type: uci
# Expected: "id name Pikafish..."
```

### 2. Chess Books (RAG Knowledge Base)

**Requirements:**
- PDF format preferred
- Ensure copyright compliance
- Text should be clear and machine-readable

**Recommended sources:**
- Public domain classical texts
- Licensed content with permission
- Self-created training materials

**Placement:**
```bash
data/books/
├── 橘中秘.pdf           # 朱晋桢 (明)
├── 梅花谱.pdf           # 王再越 (清)
├── 适情雅趣.pdf
└── 现代象棋布局.pdf
```

**Vectorization (Sprint 2.1):**
```bash
python scripts/vectorize_books.py
```

### 3. Game Database (Knowledge Graph)

**Format:**
- PGN (Portable Game Notation) files
- Should include move quality annotations when possible

**Sources:**
- Professional tournament records
- Historical games with annotations
- Your own game collection

**Placement:**
```bash
data/games/
├── professional_2020-2024.pgn
├── classical_games.pgn
└── annotated_games.pgn
```

**Import to Neo4j (Sprint 2.1):**
```bash
python scripts/import_to_neo4j.py
```

### 4. Neo4j Database Setup

**Option A: Docker (Recommended)**
```bash
docker run -d \
  --name xiangqi-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/xiangqi123 \
  -v $(pwd)/data/graph_db:/data \
  neo4j:latest
```

**Option B: Local Installation**
- Download: https://neo4j.com/download/
- Configure: Set `dbms.active_database` to point to `data/graph_db`

**Access:**
- Browser: http://localhost:7474
- Bolt: bolt://localhost:7687

### 5. Vector Database Setup

**Models Required:**
- Embedding: `BAAI/bge-m3` (BGE-M3)
- Supports Chinese text and multi-lingual content

**Index Creation (Sprint 2.1):**
```bash
# Will be created automatically by vectorize_books.py
python scripts/vectorize_books.py --books-dir data/books --output-dir data/vector_db
```

**Expected output:**
```
data/vector_db/
├── books.index      # FAISS index file
├── books.meta       # Metadata (book names, page numbers)
└── config.json      # Embedding model config
```

## Current Status (Sprint 2.0)

**No resources needed yet!** Sprint 2.0 uses Mock implementations:
- MockEngine: Simulates Pikafish responses
- MockKG: Simulates Neo4j queries
- MockRAG: Simulates book retrieval

**Sprint 2.1 will require real resources** for production use.

## Configuration

See `config/settings.yaml` (to be created in Sprint 2.1) for:
- Engine paths
- Database connection strings
- Model settings
- API keys

## Notes

- Do not commit large binary files to Git
- Add `*.pdf`, `*.pgn`, `*.index`, `pikafish*` to `.gitignore`
- Resource files can be large (100MB-1GB+)
- Consider using Git LFS or separate storage for large files
