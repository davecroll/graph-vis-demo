"""Node detail endpoint."""

from typing import Any

from fastapi import APIRouter, HTTPException

import db
from models import NodeDetail

router = APIRouter()


@router.get("/api/node/{label}/{name}")
async def get_node(label: str, name: str) -> NodeDetail:
    """Return node properties and all connected nodes."""
    records, _, _ = db.driver.execute_query(
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

    connections: list[dict[str, Any]] = []
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

    return NodeDetail(
        label=label,
        name=name,
        properties=properties,
        connections=connections,
    )
