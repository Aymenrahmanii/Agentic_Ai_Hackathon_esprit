import json
import os
from typing import Any

import pytest

from afi_agent.config import PROJECT_ROOT, load_settings
from afi_agent.graph_export import load_into_neo4j, split_statements
from afi_agent.graph_store import (
    DATASET,
    GOVERNORATES,
    LOTS,
    PROCEDURES,
    RESERVE,
    ZONES,
    Neo4jStore,
    neo4j_driver,
)
from afi_agent.models import SeedData
from afi_agent.store import InMemoryStore


def seed() -> SeedData:
    return SeedData.model_validate(
        json.loads(load_settings().seed_path.read_text(encoding="utf-8"))
    )


class Record(dict):
    def data(self) -> dict[str, Any]:
        return dict(self)


class Result(list):
    def consume(self) -> None:
        return None


class FakeSession:
    """Answers the store's queries the way Neo4j would for a graph loaded from the seed."""

    def __init__(self, data: SeedData, writes: list) -> None:
        self._data = data
        self._writes = writes

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def run(self, query: str, **parameters: Any) -> Result:
        d = self._data
        if query == DATASET:
            return Result([Record(synthetic=d.synthetic, note=d.note)])
        if query == GOVERNORATES:
            return Result(Record(name=g.name, aliases=g.aliases) for g in d.governorates)
        if query == ZONES:
            return Result(
                Record(z.model_dump(), sectors=list(reversed(z.sectors))) for z in d.zones
            )
        if query == LOTS:
            return Result(Record(lot.model_dump()) for lot in d.lots)
        if query == PROCEDURES:
            return Result(Record(p.model_dump()) for p in d.procedures)
        if query == RESERVE:
            self._writes.append(parameters)
            return Result()
        raise AssertionError(f"unexpected query: {query}")


class FakeDriver:
    def __init__(self, data: SeedData) -> None:
        self.writes: list = []
        self._data = data

    def session(self, database: str | None = None) -> FakeSession:
        return FakeSession(self._data, self.writes)


def test_store_built_from_the_graph_answers_like_the_json_store() -> None:
    data = seed()
    graph = Neo4jStore(FakeDriver(data))
    memory = InMemoryStore(data)

    def ids(results: list) -> list[tuple[str, str]]:
        return [(lot.id, zone.id) for lot, zone in results]

    assert graph.synthetic is True
    assert [z.id for z in graph.zones()] == [z.id for z in memory.zones()]
    # A graph has no order, so sectors come back sorted; compare what the searches return.
    assert graph.get_zone("ZI-SFX-01").sectors == sorted(memory.get_zone("ZI-SFX-01").sectors)
    for filters in ({"governorate": "Kairouan", "sector": "textile"}, {"max_price_tnd": 150000}):
        assert ids(graph.search_lots(**filters)) == ids(memory.search_lots(**filters))
    assert graph.resolve_governorate("القيروان") == "Kairouan"
    assert graph.get_procedure("reservation_lot") == memory.get_procedure("reservation_lot")


def test_reservations_are_written_back_to_the_graph() -> None:
    driver = FakeDriver(seed())
    store = Neo4jStore(driver)

    store.reserve_lot("L-KAI-001")

    assert driver.writes == [{"lot_id": "L-KAI-001"}]
    assert store.get_lot("L-KAI-001").status == "reserved"


def test_schema_file_splits_into_runnable_statements() -> None:
    schema = (PROJECT_ROOT / "graph" / "schema.cypher").read_text(encoding="utf-8")
    statements = split_statements(schema)

    assert len(statements) == 9
    assert all(s.startswith("CREATE") and "//" not in s for s in statements)


@pytest.mark.skipif(
    not os.environ.get("NEO4J_PASSWORD"), reason="needs a running Neo4j (set NEO4J_PASSWORD)"
)
def test_round_trip_through_a_real_neo4j() -> None:
    data = seed()
    load_into_neo4j(data, PROJECT_ROOT / "graph" / "schema.cypher")

    with neo4j_driver() as driver:
        store = Neo4jStore(driver)
        memory = InMemoryStore(data)
        assert [(lot.id, zone.id) for lot, zone in store.search_lots()] == [
            (lot.id, zone.id) for lot, zone in memory.search_lots()
        ]
        assert store.get_procedure("reservation_lot") == memory.get_procedure("reservation_lot")
