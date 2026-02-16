"""Graph endpoints for vis.js visualization."""

from fastapi import APIRouter, HTTPException

import db
from graph_utils import add_edge, build_vis_edge, ensure_node, node_id
from models import GraphResponse

router = APIRouter()


@router.get("/api/graph/{label}/{name}")
async def get_entity_graph(label: str, name: str) -> GraphResponse:
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

    records, _, _ = db.driver.execute_query(query, name=name, database_="neo4j")
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
                ensure_node(node, nodes_map, inner_ids)

        for node_key in outer_keys:
            node = record.get(node_key)
            if node is not None:
                ensure_node(node, nodes_map)

        # borrower -> deal
        if record.get("r1") is not None:
            b_id = node_id("Borrower", record["b"]["name"])
            d_id = node_id("Deal", record["d"]["name"])
            add_edge(record["r1"], b_id, d_id, edges, edge_set)

        # lender -> deal
        if record.get("r2") is not None:
            l_id = node_id("Lender", record["l"]["name"])
            d_id = node_id("Deal", record["d"]["name"])
            add_edge(record["r2"], l_id, d_id, edges, edge_set)

        # outer hop: lender/borrower -> deal2 (r4)
        if record.get("r4") is not None and record.get("d2") is not None:
            if label == "Borrower":
                from_id = node_id("Lender", record["l"]["name"])
            else:
                from_id = node_id("Borrower", record["b"]["name"])
            d2_id = node_id("Deal", record["d2"]["name"])
            add_edge(record["r4"], from_id, d2_id, edges, edge_set)

        # outer hop: borrower2/lender2 -> deal2 (r5)
        if record.get("r5") is not None and record.get("d2") is not None:
            outer_label = "Borrower" if label == "Borrower" else "Lender"
            outer_key = "b2" if label == "Borrower" else "l2"
            outer_node = record.get(outer_key)
            if outer_node is not None:
                outer_id = node_id(outer_label, outer_node["name"])
                d2_id = node_id("Deal", record["d2"]["name"])
                add_edge(record["r5"], outer_id, d2_id, edges, edge_set)

    # Fade outer-hop nodes: smaller size, dimmer color
    for nid, node_data in nodes_map.items():
        if nid not in inner_ids:
            node_data["size"] = int(node_data["size"] * 0.6)
            node_data["color"] = {"background": node_data["color"], "opacity": 0.45}
            node_data["font"] = {"color": "#707090"}

    return GraphResponse(nodes=list(nodes_map.values()), edges=edges)


@router.get("/api/graph")
async def get_graph() -> GraphResponse:
    """Return all nodes and edges formatted for vis.js Network."""
    records, _, _ = db.driver.execute_query(
        """MATCH (n)
           OPTIONAL MATCH (n)-[r]->(m)
           RETURN n, r, m""",
        database_="neo4j",
    )

    nodes_map: dict[str, dict] = {}
    edges: list[dict] = []

    for record in records:
        nid = ensure_node(record["n"], nodes_map)

        rel = record["r"]
        target = record["m"]
        if rel is not None and target is not None:
            tid = ensure_node(target, nodes_map)
            edges.append(build_vis_edge(rel, nid, tid))

    return GraphResponse(nodes=list(nodes_map.values()), edges=edges)
