# Direct Lending Graph Visualization

Interactive graph visualization of direct lending deal data — borrowers, lenders, deals, and sectors — using Neo4j, FastAPI, and vis.js Network.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- Python 3.10+

## Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# 1. Start Neo4j
docker compose up -d

# 2. Wait ~10 seconds for Neo4j to be ready, then seed the database
python seed_data.py

# 3. Start the API server
uvicorn main:app --reload
```

Open http://localhost:8000 to view the interactive graph.

Neo4j Browser is available at http://localhost:7474 (login: `neo4j` / `demo1234`).

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Serve the frontend |
| `GET /api/graph` | All nodes and edges formatted for vis.js |
| `GET /api/node/{label}/{name}` | Node detail + connections |
| `GET /api/stats` | Summary counts and totals |

## Data Model

- **Borrowers** (8) — companies like MedTech Solutions, CloudSecure Inc
- **Lenders** (6) — BDCs and credit funds like Ares Capital, HPS Investment
- **Deals** (10) — term loans, revolvers, unitranche facilities
- **Sectors** (5) — Healthcare, Technology, Industrials, Business Services, Consumer

Relationships: `BORROWED`, `LENT_TO` (with commitment amount and role), `IN_SECTOR`.

## Graph Interaction

- **Click** a node to see its properties and connections in the sidebar
- **Hover** over nodes and edges for tooltip details
- **Scroll** to zoom, **drag** to pan
- Click connections in the sidebar to navigate to related nodes
