"""Turn the seed data into Cypher statements for Neo4j.

Usage:
  python -m afi_agent.graph_export graph/seed.cypher   write a Cypher file
  python -m afi_agent.graph_export load                load schema and seed into Neo4j
"""

import json
import sys
from pathlib import Path

from afi_agent.config import load_settings
from afi_agent.models import SeedData

CypherValue = str | int | float | bool | list[str]


def cypher_literal(value: CypherValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(cypher_literal(item) for item in value) + "]"
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def seed_to_cypher(seed: SeedData) -> str:
    q = cypher_literal
    statements: list[str] = []

    for g in seed.governorates:
        statements.append(
            f"MERGE (g:Governorate {{name: {q(g.name)}}}) SET g.aliases = {q(g.aliases)}"
        )

    for z in seed.zones:
        statements.append(
            f"MERGE (z:Zone {{id: {q(z.id)}}}) "
            f"SET z.name = {q(z.name)}, z.area_ha = {q(z.area_ha)}, "
            f"z.regional_development_zone = {q(z.regional_development_zone)}, "
            f"z.location = point({{latitude: {q(z.lat)}, longitude: {q(z.lon)}}})"
        )
        statements.append(
            f"MATCH (z:Zone {{id: {q(z.id)}}}), (g:Governorate {{name: {q(z.governorate)}}}) "
            "MERGE (z)-[:LOCATED_IN]->(g)"
        )
        for sector in z.sectors:
            statements.append(
                f"MATCH (z:Zone {{id: {q(z.id)}}}) MERGE (s:Sector {{name: {q(sector)}}}) "
                "MERGE (z)-[:TARGETS]->(s)"
            )
        for item in z.infrastructure:
            statements.append(
                f"MATCH (z:Zone {{id: {q(z.id)}}}) MERGE (i:Infrastructure {{name: {q(item)}}}) "
                "MERGE (z)-[:HAS_INFRASTRUCTURE]->(i)"
            )

    for lot in seed.lots:
        statements.append(
            f"MATCH (z:Zone {{id: {q(lot.zone_id)}}}) MERGE (l:Lot {{id: {q(lot.id)}}}) "
            f"SET l.area_m2 = {q(lot.area_m2)}, l.price_tnd_per_m2 = {q(lot.price_tnd_per_m2)}, "
            f"l.status = {q(lot.status)} MERGE (l)-[:PART_OF]->(z)"
        )

    for p in seed.procedures:
        statements.append(
            f"MERGE (p:Procedure {{id: {q(p.id)}}}) "
            f"SET p.title = {q(p.title)}, p.steps = {q(p.steps)}, p.verified = {q(p.verified)}"
        )
        for position, document in enumerate(p.documents):
            statements.append(
                f"MATCH (p:Procedure {{id: {q(p.id)}}}) MERGE (d:Document {{name: {q(document)}}}) "
                f"MERGE (p)-[r:REQUIRES]->(d) SET r.position = {position}"
            )

    # Whether the data is real travels with the graph, so the app can warn about demo data.
    statements.append(
        f"MERGE (m:Dataset {{key: 'seed'}}) SET m.synthetic = {q(seed.synthetic)}, "
        f"m.note = {q(seed.note)}"
    )
    return ";\n".join(statements) + ";\n"


def split_statements(cypher: str) -> list[str]:
    """Statements of a Cypher file, without comments, for running them one by one."""
    lines = [line for line in cypher.splitlines() if not line.strip().startswith("//")]
    return [s.strip() for s in "\n".join(lines).split(";\n") if s.strip().rstrip(";")]


def load_into_neo4j(seed: SeedData, schema_path: Path) -> int:
    """Create the schema and load the seed straight into Neo4j (NEO4J_* settings)."""
    from afi_agent.graph_store import neo4j_driver  # needs the optional `graph` extra

    statements = split_statements(schema_path.read_text(encoding="utf-8"))
    statements += split_statements(seed_to_cypher(seed))
    with neo4j_driver() as driver, driver.session() as session:
        for statement in statements:
            session.run(statement.rstrip(";")).consume()
    return len(statements)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    seed_path = load_settings().seed_path
    seed = SeedData.model_validate(json.loads(seed_path.read_text(encoding="utf-8")))
    if argv[1] == "load":
        schema = Path(__file__).resolve().parents[2] / "graph" / "schema.cypher"
        count = load_into_neo4j(seed, schema)
        print(f"Ran {count} statements against Neo4j from {seed_path}")
        return 0
    Path(argv[1]).write_text(seed_to_cypher(seed), encoding="utf-8")
    print(f"Wrote {argv[1]} from {seed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
