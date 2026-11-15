"""Knowledge store backed by Neo4j.

The graph is the source of truth: at startup the store reads zones, lots and procedures from
Neo4j, answers searches with the same tested logic as the in-memory store, and writes
reservations back to the graph. Needs the optional extra: `uv sync --extra graph`.
"""

import os
from typing import Any, Protocol

from afi_agent.models import SeedData
from afi_agent.store import InMemoryStore

GOVERNORATES = """
MATCH (g:Governorate)
RETURN g.name AS name, coalesce(g.aliases, []) AS aliases
ORDER BY name
"""

ZONES = """
MATCH (z:Zone)-[:LOCATED_IN]->(g:Governorate)
OPTIONAL MATCH (z)-[:TARGETS]->(s:Sector)
OPTIONAL MATCH (z)-[:HAS_INFRASTRUCTURE]->(i:Infrastructure)
RETURN z.id AS id, z.name AS name, g.name AS governorate, z.area_ha AS area_ha,
       z.regional_development_zone AS regional_development_zone,
       z.location.latitude AS lat, z.location.longitude AS lon,
       collect(DISTINCT s.name) AS sectors, collect(DISTINCT i.name) AS infrastructure
ORDER BY id
"""

LOTS = """
MATCH (l:Lot)-[:PART_OF]->(z:Zone)
RETURN l.id AS id, z.id AS zone_id, l.area_m2 AS area_m2,
       l.price_tnd_per_m2 AS price_tnd_per_m2, l.status AS status
ORDER BY id
"""

PROCEDURES = """
MATCH (p:Procedure)
OPTIONAL MATCH (p)-[r:REQUIRES]->(d:Document)
WITH p, d, r ORDER BY r.position
RETURN p.id AS id, p.title AS title, p.steps AS steps, coalesce(p.verified, false) AS verified,
       [doc IN collect(d.name) WHERE doc IS NOT NULL] AS documents
ORDER BY id
"""

DATASET = "MATCH (m:Dataset {key: 'seed'}) RETURN m.synthetic AS synthetic, m.note AS note"

RESERVE = "MATCH (l:Lot {id: $lot_id}) SET l.status = 'reserved'"


class Session(Protocol):
    def run(self, query: str, **parameters: Any) -> Any: ...


def read_seed(session: Session) -> SeedData:
    """Build the store's data from the graph."""
    dataset = [record.data() for record in session.run(DATASET)]
    meta = dataset[0] if dataset else {"synthetic": True, "note": "No Dataset node in the graph."}
    return SeedData.model_validate(
        {
            "synthetic": bool(meta.get("synthetic", True)),
            "note": meta.get("note") or "",
            "governorates": [r.data() for r in session.run(GOVERNORATES)],
            "zones": [
                {
                    **r.data(),
                    "sectors": sorted(r["sectors"]),
                    "infrastructure": sorted(r["infrastructure"]),
                }
                for r in session.run(ZONES)
            ],
            "lots": [r.data() for r in session.run(LOTS)],
            "procedures": [r.data() for r in session.run(PROCEDURES)],
        }
    )


class Neo4jStore(InMemoryStore):
    def __init__(self, driver: Any, database: str | None = None) -> None:
        self._driver = driver
        self._database = database
        with driver.session(database=database) as session:
            super().__init__(read_seed(session))

    def reserve_lot(self, lot_id: str) -> None:
        with self._driver.session(database=self._database) as session:
            session.run(RESERVE, lot_id=lot_id).consume()
        super().reserve_lot(lot_id)


def neo4j_driver() -> Any:
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise SystemExit("The Neo4j driver is missing: run `uv sync --extra graph`.") from exc
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("Set NEO4J_PASSWORD (and NEO4J_URI if Neo4j is not on localhost).")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
