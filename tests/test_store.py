import pytest

from afi_agent.store import InMemoryStore, normalize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Kairouan", "Kairouan"),
        ("القيروان", "Kairouan"),
        ("beja", "Béja"),
        ("BÉJA", "Béja"),
        ("sidi-bouzid", "Sidi Bouzid"),
        ("سيدي بوزيد", "Sidi Bouzid"),
        ("sfe9es", "Sfax"),
    ],
)
def test_resolve_governorate_handles_scripts_accents_and_case(
    store: InMemoryStore, text: str, expected: str
) -> None:
    assert store.resolve_governorate(text) == expected


def test_resolve_governorate_unknown(store: InMemoryStore) -> None:
    assert store.resolve_governorate("Atlantis") is None


def test_normalize_strips_arabic_diacritics() -> None:
    assert normalize("القَيْرَوَان") == normalize("القيروان")


def test_search_returns_only_available_lots_cheapest_first(store: InMemoryStore) -> None:
    results = store.search_lots(governorate="Kairouan")
    assert [lot.id for lot, _ in results] == ["L-KAI-001", "L-KAI-002"]


def test_search_filters_combine(store: InMemoryStore) -> None:
    results = store.search_lots(governorate="Béja", min_area_m2=5000, max_price_tnd=300_000)
    assert [lot.id for lot, _ in results] == ["L-BEJ-001"]


def test_search_by_sector_and_limit(store: InMemoryStore) -> None:
    results = store.search_lots(sector="Textile", limit=2)
    assert len(results) == 2
    assert all("textile" in zone.sectors for _, zone in results)


def test_reserve_lot_removes_it_from_search(store: InMemoryStore) -> None:
    store.reserve_lot("L-KAI-001")
    assert [lot.id for lot, _ in store.search_lots(governorate="Kairouan")] == ["L-KAI-002"]
