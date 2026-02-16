"""Borrower and lender entity listing."""

from fastapi import APIRouter

import db
from models import BorrowerSummary, EntityListResponse, LenderSummary

router = APIRouter()


@router.get("/api/entities")
async def get_entities() -> EntityListResponse:
    """Return borrowers and lenders with summary stats for the homepage."""
    borrower_records, _, _ = db.driver.execute_query(
        """MATCH (b:Borrower)-[:BORROWED]->(d:Deal)
           WITH b, count(d) AS deal_count, sum(d.amount_mm) AS total_volume_mm
           RETURN b.name AS name, b.revenue_mm AS revenue_mm,
                  deal_count, total_volume_mm
           ORDER BY b.name""",
        database_="neo4j",
    )
    lender_records, _, _ = db.driver.execute_query(
        """MATCH (l:Lender)-[p:LENT_TO]->(d:Deal)
           WITH l, count(d) AS deal_count, sum(p.commitment_mm) AS total_commitment_mm
           RETURN l.name AS name, l.aum_bn AS aum_bn,
                  deal_count, total_commitment_mm
           ORDER BY l.name""",
        database_="neo4j",
    )
    return EntityListResponse(
        borrowers=[BorrowerSummary(**dict(r)) for r in borrower_records],
        lenders=[LenderSummary(**dict(r)) for r in lender_records],
    )
