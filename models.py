"""Pydantic response models."""

from typing import Any

from pydantic import BaseModel, Field


class BorrowerSummary(BaseModel):
    name: str
    revenue_mm: float | None = None
    deal_count: int
    total_volume_mm: float | None = None


class LenderSummary(BaseModel):
    name: str
    aum_bn: float | None = None
    deal_count: int
    total_commitment_mm: float | None = None


class EntityListResponse(BaseModel):
    borrowers: list[BorrowerSummary]
    lenders: list[LenderSummary]


class VisNode(BaseModel, extra="allow"):
    id: str
    label: str
    group: str
    title: str


class VisEdge(BaseModel, extra="allow"):
    from_field: str = Field(alias="from")
    to: str
    label: str
    title: str
    arrows: str

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class GraphResponse(BaseModel):
    nodes: list[VisNode]
    edges: list[VisEdge]


class Connection(BaseModel, extra="allow"):
    relationship: str
    relationship_props: dict[str, Any]
    node_label: str
    node_name: str
    node_props: dict[str, Any]


class NodeDetail(BaseModel):
    label: str
    name: str
    properties: dict[str, Any]
    connections: list[Connection]


class StatsResponse(BaseModel):
    borrowers: int
    lenders: int
    deals: int
    sectors: int
    total_deal_volume_mm: float
