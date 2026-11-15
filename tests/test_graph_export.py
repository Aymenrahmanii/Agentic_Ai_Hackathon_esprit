import json

from afi_agent.config import load_settings
from afi_agent.graph_export import cypher_literal, seed_to_cypher
from afi_agent.models import SeedData


def test_cypher_literal_escapes_quotes_and_backslashes() -> None:
    assert cypher_literal("Réservation d'un lot") == "'Réservation d\\'un lot'"
    assert cypher_literal("a\\b") == "'a\\\\b'"
    assert cypher_literal(True) == "true"
    assert cypher_literal(42.5) == "42.5"
    assert cypher_literal(["a", "b"]) == "['a', 'b']"


def test_seed_export_covers_every_node_and_relationship() -> None:
    seed_path = load_settings().seed_path
    seed = SeedData.model_validate(json.loads(seed_path.read_text(encoding="utf-8")))

    cypher = seed_to_cypher(seed)

    for zone in seed.zones:
        assert f"MERGE (z:Zone {{id: '{zone.id}'}})" in cypher
    for lot in seed.lots:
        assert f"MERGE (l:Lot {{id: '{lot.id}'}})" in cypher
    for relationship in ("LOCATED_IN", "TARGETS", "HAS_INFRASTRUCTURE", "PART_OF"):
        assert f"[:{relationship}]" in cypher
    assert "[r:REQUIRES]" in cypher and "r.position = 0" in cypher
    assert "MERGE (m:Dataset {key: 'seed'}) SET m.synthetic = true" in cypher
    assert all(line.endswith(";") for line in cypher.strip().splitlines())
