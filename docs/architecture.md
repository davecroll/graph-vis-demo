# Direct Lending Graph — Architecture

> Based on the [arc42 template](https://arc42.org/overview). Sections that don't apply to this project are omitted.

---

## 1. Introduction and Goals

### Purpose

Interactive graph visualization of direct lending relationships — borrowers, lenders, deals, and sectors. Built as a demo/prototype for exploring network effects in a lending portfolio.

### Key Requirements

| Priority | Requirement |
|----------|------------|
| Must | Visualize borrower-lender-deal relationships as an interactive graph |
| Must | Drill into any entity to see its properties and connections |
| Must | Show summary statistics across the portfolio |
| Should | Highlight indirect connections (e.g., lenders that share deals with a borrower) |

### Quality Goals

| Goal | Description |
|------|------------|
| Simplicity | Single-server deployment, no build step for frontend |
| Explorable | Swagger/OpenAPI docs auto-generated from typed response models |
| Configurable | Database connection externalized via environment variables |

---

## 2. Constraints

| Constraint | Details |
|-----------|---------|
| Language | Python 3.13 |
| Database | Neo4j (graph database) — chosen because the domain is inherently a network |
| Frontend | vis.js for graph rendering, vanilla HTML/JS (no framework) |
| Deployment | Local development only (no containerization yet) |

---

## 3. Context and Scope

How the system sits in its environment.

```mermaid
graph TB
    Browser["Browser<br/>(vis.js + HTML)"]
    FastAPI["FastAPI Server<br/>(uvicorn)"]
    Neo4j["Neo4j<br/>(bolt://localhost:7687)"]

    Browser -- "HTTP GET /api/*<br/>JSON responses" --> FastAPI
    Browser -- "HTTP GET /<br/>Static HTML/JS/CSS" --> FastAPI
    FastAPI -- "Bolt protocol<br/>Cypher queries" --> Neo4j
```

| Component | Responsibility |
|-----------|---------------|
| Browser | Renders interactive graph (vis.js), fetches data from API |
| FastAPI Server | Serves static frontend, exposes JSON API, transforms Neo4j results into vis.js format |
| Neo4j | Stores and queries the lending graph |

---

## 4. Building Block View

### Level 1 — Data Model

```mermaid
erDiagram
    Borrower {
        string name
        float revenue_mm
        float ebitda_mm
        string hq
    }
    Lender {
        string name
        string type
        float aum_bn
    }
    Deal {
        string name
        string type
        float amount_mm
        int spread_bps
        string maturity
    }
    Sector {
        string name
    }

    Borrower ||--o{ Deal : "BORROWED"
    Lender  }o--o{ Deal : "LENT_TO (commitment_mm, role)"
    Borrower }o--|| Sector : "IN_SECTOR"
```

### Level 2 — Module Structure

```
main.py              App shell, static files, router wiring
config.py            Settings (pydantic-settings, env var overrides)
db.py                Neo4j driver lifecycle
models.py            Pydantic response models (API contract)
graph_utils.py       vis.js node/edge building helpers
routes/
  entities.py        GET /api/entities
  graph.py           GET /api/graph, GET /api/graph/{label}/{name}
  nodes.py           GET /api/node/{label}/{name}
  stats.py           GET /api/stats
static/              Frontend HTML/JS/CSS
seed_data.py         Populates Neo4j with demo data
```

```mermaid
graph TD
    main["main.py<br/><i>App shell, static files,<br/>router wiring</i>"]
    db["db.py<br/><i>Neo4j driver, lifespan</i>"]
    config["config.py<br/><i>Settings via pydantic-settings</i>"]
    models["models.py<br/><i>Pydantic response models</i>"]
    graph_utils["graph_utils.py<br/><i>vis.js node/edge builders</i>"]
    entities["routes/entities.py"]
    graphRoutes["routes/graph.py"]
    nodes["routes/nodes.py"]
    stats["routes/stats.py"]

    main --> db
    main --> entities
    main --> graphRoutes
    main --> nodes
    main --> stats

    db --> config

    entities --> db
    entities --> models

    graphRoutes --> db
    graphRoutes --> models
    graphRoutes --> graph_utils

    nodes --> db
    nodes --> models

    stats --> db
    stats --> models
```

---

## 5. Runtime View

### Scenario: Loading a Borrower's Entity Page

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as FastAPI
    participant N as Neo4j

    B->>F: GET /entity/Borrower/MedTech%20Solutions
    F-->>B: entity.html (static)

    B->>F: GET /api/node/Borrower/MedTech%20Solutions
    F->>N: MATCH (n:Borrower) ... RETURN n, r, m
    N-->>F: Records (node + connections)
    F-->>B: NodeDetail JSON

    B->>F: GET /api/graph/Borrower/MedTech%20Solutions
    F->>N: MATCH (b:Borrower)-[r1:BORROWED]->(d:Deal) ...
    N-->>F: Records (nodes + rels)
    Note over F: build_vis_node / build_vis_edge<br/>fade outer-hop nodes
    F-->>B: GraphResponse JSON

    Note over B: vis.js renders network graph
```

The entity graph query uses a 2-hop pattern: it fetches the target entity's direct deals, then follows one more hop to find other entities sharing those deals. Outer-hop nodes are rendered with reduced opacity to visually distinguish direct from indirect connections.

---

## 6. API Reference

All endpoints return typed Pydantic models. Full schemas are available at `/docs` (Swagger UI) when the server is running.

| Endpoint | Response Model | Description |
|----------|---------------|-------------|
| `GET /api/entities` | `EntityListResponse` | Borrowers and lenders with aggregated stats |
| `GET /api/graph` | `GraphResponse` | Full graph in vis.js format |
| `GET /api/graph/{label}/{name}` | `GraphResponse` | Entity-scoped 2-hop subgraph |
| `GET /api/node/{label}/{name}` | `NodeDetail` | Node properties + all connections |
| `GET /api/stats` | `StatsResponse` | Portfolio-level counts and totals |

---

## 7. Configuration

Settings are managed via `pydantic-settings` and can be overridden with environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `demo1234` | Neo4j password |

---

## 8. Decisions

<!-- Record key architectural decisions here as the project evolves.
     See https://adr.github.io/ for the ADR format. -->

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Neo4j over relational DB | Domain is a network of lending relationships; graph queries (multi-hop traversals, path finding) are natural in Cypher |
| D2 | vis.js for graph rendering | Mature, well-documented network visualization library; no build step required |
| D3 | Pydantic response models | Self-documenting API via OpenAPI, runtime validation catches schema drift |
| D4 | Full Neo4j nodes in graph endpoints | Graph routes need `.labels` and all properties for vis.js rendering; scalar projections used only where practical (`/api/entities`) |
| D5 | pydantic-settings for config | Standard FastAPI pattern; reads env vars with typed defaults, no extra dependencies beyond Pydantic |

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| Borrower | Company that takes on debt through a deal |
| Lender | Financial institution (BDC or credit fund) that provides capital |
| Deal | A specific lending instrument (term loan, revolver, unitranche, etc.) |
| Sector | Industry classification for a borrower |
| LENT_TO | Relationship from lender to deal, carrying `commitment_mm` (amount) and `role` (Lead Arranger, Participant, Sole Lender) |
| BORROWED | Relationship from borrower to deal (no properties) |
| Outer-hop node | A node discovered via 2-hop traversal, rendered with reduced opacity |
