"""Direct Lending Graph Visualization API."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

STYLE = {
    "Borrower": {"color": "#4A90D9", "shape": "dot", "size": 25},
    "Lender": {"color": "#5CB85C", "shape": "diamond", "size": 25},
    "Deal": {"color": "#F0AD4E", "shape": "square", "size": 20},
    "Sector": {"color": "#9B59B6", "shape": "triangle", "size": 20},
}

DEFAULT_STYLE = {"color": "#999", "shape": "dot", "size": 15}


def _node_id(label: str, name: str) -> str:
    return f"{label}:{name}"


@app.get("/entity/{label}/{name}")
async def entity_page(label: str, name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "entity.html")


def _build_vis_node(node) -> tuple[str, dict[str, Any]]:
    """Convert a Neo4j node to a vis.js node dict."""
    label = list(node.labels)[0]
    name = node["name"]
    nid = _node_id(label, name)
    style = STYLE.get(label, DEFAULT_STYLE)
    props = dict(node)
    title_lines = [f"<b>{label}: {name}</b>"]
    title_lines += [f"{k}: {v}" for k, v in props.items() if k != "name"]
    return nid, {
        "id": nid,
        "label": name,
        "group": label,
        "title": "<br>".join(title_lines),
        **style,
    }


def _build_vis_edge(rel, from_id: str, to_id: str) -> dict[str, Any]:
    """Convert a Neo4j relationship to a vis.js edge dict."""
    rel_type = rel.type
    rel_props = dict(rel)
    edge_label = rel_type.replace("_", " ")
    if "commitment_mm" in rel_props:
        edge_label += f"\n${rel_props['commitment_mm']}MM"
    title_lines = [f"<b>{rel_type}</b>"]
    title_lines += [f"{k}: {v}" for k, v in rel_props.items()]
    return {
        "from": from_id,
        "to": to_id,
        "label": edge_label,
        "title": "<br>".join(title_lines),
        "arrows": "to",
        "font": {"size": 10, "align": "middle"},
    }


def _ensure_node(
    node, nodes_map: dict[str, dict], inner_ids: set[str] | None = None
) -> str:
    """Add a node to nodes_map if not already present. Returns the node id.

    If inner_ids is provided, the node id is also added to that set.
    """
    nid, vis_node = _build_vis_node(node)
    if inner_ids is not None:
        inner_ids.add(nid)
    if nid not in nodes_map:
        nodes_map[nid] = vis_node
    return nid


def _add_edge(
    rel,
    from_id: str,
    to_id: str,
    edges: list[dict],
    edge_set: set[tuple],
) -> None:
    """Add an edge if not already in edge_set (deduplication)."""
    edge_key = (from_id, rel.type, to_id)
    if edge_key not in edge_set:
        edge_set.add(edge_key)
        edges.append(_build_vis_edge(rel, from_id, to_id))


def _records_to_entity_list(records, node_key: str, extra_keys: list[str]) -> list[dict]:
    """Convert Neo4j records to a list of dicts with node props and extra aggregation fields."""
    result = []
    for record in records:
        props = dict(record[node_key])
        for key in extra_keys:
            props[key] = record[key]
        result.append(props)
    return result


@app.get("/api/entities")
async def get_entities() -> dict[str, list[dict]]:
    """Return borrowers and lenders with summary stats for the homepage."""
    borrower_records, _, _ = driver.execute_query(
        """MATCH (b:Borrower)-[:BORROWED]->(d:Deal)
           WITH b, count(d) AS deal_count, sum(d.amount_mm) AS total_volume_mm
           RETURN b, deal_count, total_volume_mm
           ORDER BY b.name""",
        database_="neo4j",
    )
    lender_records, _, _ = driver.execute_query(
        """MATCH (l:Lender)-[p:LENT_TO]->(d:Deal)
           WITH l, count(d) AS deal_count, sum(p.commitment_mm) AS total_commitment_mm
           RETURN l, deal_count, total_commitment_mm
           ORDER BY l.name""",
        database_="neo4j",
    )
    return {
        "borrowers": _records_to_entity_list(borrower_records, "b", ["deal_count", "total_volume_mm"]),
        "lenders": _records_to_entity_list(lender_records, "l", ["deal_count", "total_commitment_mm"]),
    }


@app.get("/api/graph/{label}/{name}")
async def get_entity_graph(label: str, name: str) -> dict[str, list[dict]]:
    """Return entity-scoped graph for vis.js.

    Borrower: borrower + its deals + lenders on those deals + sector.
    Lender: lender + its deals + borrowers on those deals + their sectors.
    """
    if label == "Borrower":
        query = """
            MATCH (b:Borrower {name: $name})-[r1:BORROWED]->(d:Deal)
            OPTIONAL MATCH (l:Lender)-[r2:LENT_TO]->(d)
            OPTIONAL MATCH (l)-[r4:LENT_TO]->(d2:Deal) WHERE d2 <> d
            OPTIONAL MATCH (b2:Borrower)-[r5:BORROWED]->(d2)
            RETURN b, r1, d, l, r2, d2, r4, b2, r5
        """
        inner_keys = ("b", "d", "l")
        outer_keys = ("d2", "b2")
    elif label == "Lender":
        query = """
            MATCH (l:Lender {name: $name})-[r2:LENT_TO]->(d:Deal)
            OPTIONAL MATCH (b:Borrower)-[r1:BORROWED]->(d)
            OPTIONAL MATCH (b)-[r4:BORROWED]->(d2:Deal) WHERE d2 <> d
            OPTIONAL MATCH (l2:Lender)-[r5:LENT_TO]->(d2)
            RETURN b, r1, d, l, r2, d2, r4, l2, r5
        """
        inner_keys = ("b", "d", "l")
        outer_keys = ("d2", "l2")
    else:
        raise HTTPException(status_code=400, detail="Label must be Borrower or Lender")

    records, _, _ = driver.execute_query(query, name=name, database_="neo4j")
    if not records:
        raise HTTPException(status_code=404, detail=f"{label} '{name}' not found")

    nodes_map: dict[str, dict] = {}
    edges: list[dict] = []
    edge_set: set[tuple] = set()
    inner_ids: set[str] = set()

    for record in records:
        for node_key in inner_keys:
            node = record.get(node_key)
            if node is not None:
                _ensure_node(node, nodes_map, inner_ids)

        for node_key in outer_keys:
            node = record.get(node_key)
            if node is not None:
                _ensure_node(node, nodes_map)

        # borrower -> deal
        if record.get("r1") is not None:
            b_id = _node_id("Borrower", record["b"]["name"])
            d_id = _node_id("Deal", record["d"]["name"])
            _add_edge(record["r1"], b_id, d_id, edges, edge_set)

        # lender -> deal
        if record.get("r2") is not None:
            l_id = _node_id("Lender", record["l"]["name"])
            d_id = _node_id("Deal", record["d"]["name"])
            _add_edge(record["r2"], l_id, d_id, edges, edge_set)

        # outer hop: lender/borrower -> deal2 (r4)
        if record.get("r4") is not None and record.get("d2") is not None:
            if label == "Borrower":
                from_id = _node_id("Lender", record["l"]["name"])
            else:
                from_id = _node_id("Borrower", record["b"]["name"])
            d2_id = _node_id("Deal", record["d2"]["name"])
            _add_edge(record["r4"], from_id, d2_id, edges, edge_set)

        # outer hop: borrower2/lender2 -> deal2 (r5)
        if record.get("r5") is not None and record.get("d2") is not None:
            outer_label = "Borrower" if label == "Borrower" else "Lender"
            outer_key = "b2" if label == "Borrower" else "l2"
            outer_node = record.get(outer_key)
            if outer_node is not None:
                outer_id = _node_id(outer_label, outer_node["name"])
                d2_id = _node_id("Deal", record["d2"]["name"])
                _add_edge(record["r5"], outer_id, d2_id, edges, edge_set)

    # Fade outer-hop nodes: smaller size, dimmer color
    for nid, node_data in nodes_map.items():
        if nid not in inner_ids:
            node_data["size"] = int(node_data["size"] * 0.6)
            node_data["color"] = {"background": node_data["color"], "opacity": 0.45}
            node_data["font"] = {"color": "#707090"}

    return {"nodes": list(nodes_map.values()), "edges": edges}


@app.get("/api/graph")
async def get_graph() -> dict[str, list[dict]]:
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
        nid = _ensure_node(record["n"], nodes_map)

        rel = record["r"]
        target = record["m"]
        if rel is not None and target is not None:
            tid = _ensure_node(target, nodes_map)
            edges.append(_build_vis_edge(rel, nid, tid))

    return {"nodes": list(nodes_map.values()), "edges": edges}


@app.get("/api/node/{label}/{name}")
async def get_node(label: str, name: str) -> dict[str, Any]:
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

    properties = dict(records[0]["n"])

    connections = []
    seen: set[tuple] = set()
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
async def get_stats() -> dict[str, Any]:
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
