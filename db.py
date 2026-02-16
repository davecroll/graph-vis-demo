"""Neo4j driver management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from neo4j import GraphDatabase

from config import settings

driver = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global driver
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    driver.verify_connectivity()
    yield
    driver.close()
