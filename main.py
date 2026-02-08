"""Direct Lending Graph Visualization API."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "demo1234")

driver = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global driver
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    driver.verify_connectivity()
    yield
    driver.close()


app = FastAPI(title="Direct Lending Graph", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Vis.js node styling by label ---
STYLE = {
    "Borrower": {"color": "#4A90D9", "shape": "dot", "size": 25},
    "Lender": {"color": "#5CB85C", "shape": "diamond", "size": 25},
    "Deal": {"color": "#F0AD4E", "shape": "square", "size": 20},
    "Sector": {"color": "#9B59B6", "shape": "triangle", "size": 20},
}


def _node_id(label: str, name: str) -> str:
    return f"{label}:{name}"


@app.get("/api/graph")
async def get_graph():
    """Return all nodes and edges formatted for vis.js Network."""
    records, _, _ = driver.execute_query(
        """MATCH (n)
           OPTIONAL MATCH (n)-[r]->(m)
           RETURN n, r, m""",
        database_="neo4j",
    )

    nodes_map: dict[str, dict] = {}
    edges: list[dict] = []

    for record in records:
        node = record["n"]
        label = list(node.labels)[0]
        name = node["name"]
        nid = _node_id(label, name)

        if nid not in nodes_map:
            style = STYLE.get(label, {"color": "#999", "shape": "dot", "size": 15})
            props = dict(node)
            title_lines = [f"<b>{label}: {name}</b>"]
            for k, v in props.items():
                if k != "name":
                    title_lines.append(f"{k}: {v}")
            nodes_map[nid] = {
                "id": nid,
                "label": name,
                "group": label,
                "title": "<br>".join(title_lines),
                **style,
            }

        rel = record["r"]
        target = record["m"]
        if rel is not None and target is not None:
            t_label = list(target.labels)[0]
            t_name = target["name"]
            tid = _node_id(t_label, t_name)

            if tid not in nodes_map:
                t_style = STYLE.get(t_label, {"color": "#999", "shape": "dot", "size": 15})
                t_props = dict(target)
                t_title_lines = [f"<b>{t_label}: {t_name}</b>"]
                for k, v in t_props.items():
                    if k != "name":
                        t_title_lines.append(f"{k}: {v}")
                nodes_map[tid] = {
                    "id": tid,
                    "label": t_name,
                    "group": t_label,
                    "title": "<br>".join(t_title_lines),
                    **t_style,
                }

            rel_type = rel.type
            rel_props = dict(rel)
            edge_label = rel_type.replace("_", " ")
            if "commitment_mm" in rel_props:
                edge_label += f"\n${rel_props['commitment_mm']}MM"

            edge_title_lines = [f"<b>{rel_type}</b>"]
            for k, v in rel_props.items():
                edge_title_lines.append(f"{k}: {v}")

            edges.append({
                "from": nid,
                "to": tid,
                "label": edge_label,
                "title": "<br>".join(edge_title_lines),
                "arrows": "to",
                "font": {"size": 10, "align": "middle"},
            })

    return {"nodes": list(nodes_map.values()), "edges": edges}


@app.get("/api/node/{label}/{name}")
async def get_node(label: str, name: str):
    """Return node properties and all connected nodes."""
    records, _, _ = driver.execute_query(
        """MATCH (n)
           WHERE $label IN labels(n) AND n.name = $name
           OPTIONAL MATCH (n)-[r]-(m)
           RETURN n, r, m""",
        label=label,
        name=name,
        database_="neo4j",
    )

    if not records:
        raise HTTPException(status_code=404, detail=f"{label} '{name}' not found")

    node = records[0]["n"]
    properties = dict(node)

    connections = []
    seen = set()
    for record in records:
        rel = record["r"]
        other = record["m"]
        if rel is None or other is None:
            continue
        o_label = list(other.labels)[0]
        o_name = other["name"]
        key = (rel.type, o_label, o_name)
        if key in seen:
            continue
        seen.add(key)
        connections.append({
            "relationship": rel.type,
            "relationship_props": dict(rel),
            "node_label": o_label,
            "node_name": o_name,
            "node_props": dict(other),
        })

    return {
        "label": label,
        "name": name,
        "properties": properties,
        "connections": connections,
    }


@app.get("/api/stats")
async def get_stats():
    """Return summary counts and totals."""
    records, _, _ = driver.execute_query(
        """MATCH (b:Borrower) WITH count(b) AS borrowers
           MATCH (l:Lender) WITH borrowers, count(l) AS lenders
           MATCH (d:Deal) WITH borrowers, lenders, count(d) AS deals
           MATCH (s:Sector) WITH borrowers, lenders, deals, count(s) AS sectors
           MATCH (d2:Deal)
           RETURN borrowers, lenders, deals, sectors,
                  sum(d2.amount_mm) AS total_deal_volume_mm""",
        database_="neo4j",
    )
    row = records[0]
    return {
        "borrowers": row["borrowers"],
        "lenders": row["lenders"],
        "deals": row["deals"],
        "sectors": row["sectors"],
        "total_deal_volume_mm": row["total_deal_volume_mm"],
    }
