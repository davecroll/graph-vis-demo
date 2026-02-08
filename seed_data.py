"""Seed Neo4j with direct lending demo data."""

from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "demo1234")


def seed(tx):
    # Clear existing data
    tx.run("MATCH (n) DETACH DELETE n")

    # --- Sectors ---
    sectors = ["Healthcare", "Technology", "Industrials", "Business Services", "Consumer"]
    for s in sectors:
        tx.run("CREATE (:Sector {name: $name})", name=s)
    print(f"  Created {len(sectors)} Sectors")

    # --- Borrowers ---
    borrowers = [
        {"name": "MedTech Solutions", "sector": "Healthcare", "revenue_mm": 120, "ebitda_mm": 28, "hq": "Boston, MA"},
        {"name": "CloudSecure Inc", "sector": "Technology", "revenue_mm": 85, "ebitda_mm": 18, "hq": "Austin, TX"},
        {"name": "PrecisionMfg Corp", "sector": "Industrials", "revenue_mm": 200, "ebitda_mm": 42, "hq": "Detroit, MI"},
        {"name": "DataFlow Analytics", "sector": "Technology", "revenue_mm": 65, "ebitda_mm": 14, "hq": "San Francisco, CA"},
        {"name": "ProStaff Holdings", "sector": "Business Services", "revenue_mm": 150, "ebitda_mm": 32, "hq": "Chicago, IL"},
        {"name": "VitalCare Clinics", "sector": "Healthcare", "revenue_mm": 95, "ebitda_mm": 22, "hq": "Nashville, TN"},
        {"name": "BrightHome Brands", "sector": "Consumer", "revenue_mm": 110, "ebitda_mm": 20, "hq": "Atlanta, GA"},
        {"name": "Apex Logistics", "sector": "Industrials", "revenue_mm": 175, "ebitda_mm": 38, "hq": "Dallas, TX"},
    ]
    for b in borrowers:
        tx.run(
            """CREATE (b:Borrower {name: $name, revenue_mm: $revenue_mm,
               ebitda_mm: $ebitda_mm, hq: $hq})
               WITH b
               MATCH (s:Sector {name: $sector})
               CREATE (b)-[:IN_SECTOR]->(s)""",
            **b,
        )
    print(f"  Created {len(borrowers)} Borrowers + IN_SECTOR links")

    # --- Lenders ---
    lenders = [
        {"name": "Ares Capital", "type": "BDC", "aum_bn": 21.0},
        {"name": "HPS Investment", "type": "Credit Fund", "aum_bn": 12.0},
        {"name": "Golub Capital", "type": "BDC", "aum_bn": 9.5},
        {"name": "Blue Owl Capital", "type": "Credit Fund", "aum_bn": 15.0},
        {"name": "Monroe Capital", "type": "Credit Fund", "aum_bn": 4.2},
        {"name": "Owl Rock (Blue Owl)", "type": "BDC", "aum_bn": 11.0},
    ]
    for l in lenders:
        tx.run(
            "CREATE (:Lender {name: $name, type: $type, aum_bn: $aum_bn})",
            **l,
        )
    print(f"  Created {len(lenders)} Lenders")

    # --- Deals ---
    deals = [
        {"name": "MedTech Term Loan A", "borrower": "MedTech Solutions", "type": "Term Loan", "amount_mm": 75, "spread_bps": 550, "maturity": "2029-06"},
        {"name": "MedTech Revolver", "borrower": "MedTech Solutions", "type": "Revolver", "amount_mm": 15, "spread_bps": 500, "maturity": "2028-06"},
        {"name": "CloudSecure Unitranche", "borrower": "CloudSecure Inc", "type": "Unitranche", "amount_mm": 50, "spread_bps": 625, "maturity": "2030-03"},
        {"name": "PrecisionMfg TL-B", "borrower": "PrecisionMfg Corp", "type": "Term Loan B", "amount_mm": 130, "spread_bps": 500, "maturity": "2029-12"},
        {"name": "DataFlow Growth Facility", "borrower": "DataFlow Analytics", "type": "Delayed Draw TL", "amount_mm": 40, "spread_bps": 600, "maturity": "2030-06"},
        {"name": "ProStaff Acquisition Fin", "borrower": "ProStaff Holdings", "type": "Term Loan", "amount_mm": 100, "spread_bps": 575, "maturity": "2029-09"},
        {"name": "VitalCare Unitranche", "borrower": "VitalCare Clinics", "type": "Unitranche", "amount_mm": 60, "spread_bps": 650, "maturity": "2030-01"},
        {"name": "BrightHome TL", "borrower": "BrightHome Brands", "type": "Term Loan", "amount_mm": 55, "spread_bps": 525, "maturity": "2029-03"},
        {"name": "Apex Logistics Refi", "borrower": "Apex Logistics", "type": "Term Loan", "amount_mm": 110, "spread_bps": 475, "maturity": "2028-12"},
        {"name": "Apex Revolver", "borrower": "Apex Logistics", "type": "Revolver", "amount_mm": 25, "spread_bps": 425, "maturity": "2027-12"},
    ]
    for d in deals:
        tx.run(
            """CREATE (deal:Deal {name: $name, type: $type, amount_mm: $amount_mm,
               spread_bps: $spread_bps, maturity: $maturity})
               WITH deal
               MATCH (b:Borrower {name: $borrower})
               CREATE (b)-[:BORROWED]->(deal)""",
            **d,
        )
    print(f"  Created {len(deals)} Deals + BORROWED links")

    # --- Lender participations (LENT_TO) ---
    # Ares in 4 deals, HPS in 3 => hub nodes
    participations = [
        # MedTech Term Loan A - syndicated
        {"lender": "Ares Capital", "deal": "MedTech Term Loan A", "commitment_mm": 40, "role": "Lead Arranger"},
        {"lender": "HPS Investment", "deal": "MedTech Term Loan A", "commitment_mm": 35, "role": "Participant"},
        # MedTech Revolver
        {"lender": "Ares Capital", "deal": "MedTech Revolver", "commitment_mm": 15, "role": "Sole Lender"},
        # CloudSecure Unitranche
        {"lender": "Blue Owl Capital", "deal": "CloudSecure Unitranche", "commitment_mm": 30, "role": "Lead Arranger"},
        {"lender": "Monroe Capital", "deal": "CloudSecure Unitranche", "commitment_mm": 20, "role": "Participant"},
        # PrecisionMfg TL-B - 3-lender syndicate
        {"lender": "Ares Capital", "deal": "PrecisionMfg TL-B", "commitment_mm": 55, "role": "Lead Arranger"},
        {"lender": "Golub Capital", "deal": "PrecisionMfg TL-B", "commitment_mm": 40, "role": "Participant"},
        {"lender": "HPS Investment", "deal": "PrecisionMfg TL-B", "commitment_mm": 35, "role": "Participant"},
        # DataFlow Growth Facility
        {"lender": "HPS Investment", "deal": "DataFlow Growth Facility", "commitment_mm": 40, "role": "Sole Lender"},
        # ProStaff Acquisition Fin - 2-lender
        {"lender": "Blue Owl Capital", "deal": "ProStaff Acquisition Fin", "commitment_mm": 60, "role": "Lead Arranger"},
        {"lender": "Golub Capital", "deal": "ProStaff Acquisition Fin", "commitment_mm": 40, "role": "Participant"},
        # VitalCare Unitranche
        {"lender": "Owl Rock (Blue Owl)", "deal": "VitalCare Unitranche", "commitment_mm": 60, "role": "Sole Lender"},
        # BrightHome TL
        {"lender": "Monroe Capital", "deal": "BrightHome TL", "commitment_mm": 30, "role": "Lead Arranger"},
        {"lender": "Owl Rock (Blue Owl)", "deal": "BrightHome TL", "commitment_mm": 25, "role": "Participant"},
        # Apex Logistics Refi - big syndicate
        {"lender": "Ares Capital", "deal": "Apex Logistics Refi", "commitment_mm": 50, "role": "Lead Arranger"},
        {"lender": "Blue Owl Capital", "deal": "Apex Logistics Refi", "commitment_mm": 35, "role": "Participant"},
        {"lender": "Golub Capital", "deal": "Apex Logistics Refi", "commitment_mm": 25, "role": "Participant"},
        # Apex Revolver
        {"lender": "Ares Capital", "deal": "Apex Revolver", "commitment_mm": 25, "role": "Sole Lender"},
    ]
    for p in participations:
        tx.run(
            """MATCH (l:Lender {name: $lender}), (d:Deal {name: $deal})
               CREATE (l)-[:LENT_TO {commitment_mm: $commitment_mm, role: $role}]->(d)""",
            **p,
        )
    print(f"  Created {len(participations)} LENT_TO relationships")


def main():
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    print("Connected. Seeding data...")

    with driver.session() as session:
        session.execute_write(seed)

    driver.close()
    print("Done! Seeded 29 nodes and 36 relationships.")


if __name__ == "__main__":
    main()
