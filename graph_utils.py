"""Vis.js graph building helpers."""

from typing import Any

STYLE = {
    "Borrower": {"color": "#4A90D9", "shape": "dot", "size": 25},
    "Lender": {"color": "#5CB85C", "shape": "diamond", "size": 25},
    "Deal": {"color": "#F0AD4E", "shape": "square", "size": 20},
    "Sector": {"color": "#9B59B6", "shape": "triangle", "size": 20},
}

DEFAULT_STYLE = {"color": "#999", "shape": "dot", "size": 15}


def node_id(label: str, name: str) -> str:
    return f"{label}:{name}"


def build_vis_node(node) -> tuple[str, dict[str, Any]]:
    """Convert a Neo4j node to a vis.js node dict."""
    label = list(node.labels)[0]
    name = node["name"]
    nid = node_id(label, name)
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


def build_vis_edge(rel, from_id: str, to_id: str) -> dict[str, Any]:
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


def ensure_node(
    node, nodes_map: dict[str, dict], inner_ids: set[str] | None = None
) -> str:
    """Add a node to nodes_map if not already present. Returns the node id.

    If inner_ids is provided, the node id is also added to that set.
    """
    nid, vis_node = build_vis_node(node)
    if inner_ids is not None:
        inner_ids.add(nid)
    if nid not in nodes_map:
        nodes_map[nid] = vis_node
    return nid


def add_edge(
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
        edges.append(build_vis_edge(rel, from_id, to_id))
