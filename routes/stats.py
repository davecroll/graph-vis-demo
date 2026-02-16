"""Summary statistics endpoint."""

from fastapi import APIRouter

import db
from models import StatsResponse

router = APIRouter()


@router.get("/api/stats")
async def get_stats() -> StatsResponse:
    """Return summary counts and totals."""
    records, _, _ = db.driver.execute_query(
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
    return StatsResponse(
        borrowers=row["borrowers"],
        lenders=row["lenders"],
        deals=row["deals"],
        sectors=row["sectors"],
        total_deal_volume_mm=row["total_deal_volume_mm"],
    )
