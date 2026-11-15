import json
import re
import unicodedata
from pathlib import Path
from typing import Protocol, Self

from afi_agent.models import Lot, Procedure, SeedData, Zone

_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


def normalize(text: str) -> str:
    """Fold case, accents, Arabic diacritics and punctuation so names compare loosely."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _NON_WORD.sub("", without_marks)


class KnowledgeStore(Protocol):
    """Read side of the knowledge graph. Swap InMemoryStore for a Neo4j-backed one later."""

    def governorates(self) -> list[str]: ...

    def resolve_governorate(self, text: str) -> str | None: ...

    def zones(self) -> list[Zone]: ...

    def get_zone(self, zone_id: str) -> Zone | None: ...

    def get_lot(self, lot_id: str) -> Lot | None: ...

    def lots_in_zone(self, zone_id: str) -> list[Lot]: ...

    def search_lots(
        self,
        *,
        governorate: str | None = None,
        sector: str | None = None,
        min_area_m2: float | None = None,
        max_price_tnd: float | None = None,
        limit: int = 5,
    ) -> list[tuple[Lot, Zone]]: ...

    def procedures(self) -> list[Procedure]: ...

    def get_procedure(self, procedure_id: str) -> Procedure | None: ...

    def reserve_lot(self, lot_id: str) -> None: ...


class InMemoryStore:
    def __init__(self, seed: SeedData) -> None:
        # Whether this is invented demo data, so the interface can say so.
        self.synthetic = seed.synthetic
        self.data_note = seed.note
        self._zones = {zone.id: zone for zone in seed.zones}
        self._lots = {lot.id: lot for lot in seed.lots}
        self._procedures = {procedure.id: procedure for procedure in seed.procedures}
        self._governorates = [g.name for g in seed.governorates]
        self._aliases = {
            normalize(alias): g.name for g in seed.governorates for alias in (g.name, *g.aliases)
        }

    @classmethod
    def from_file(cls, path: Path) -> Self:
        return cls(SeedData.model_validate(json.loads(path.read_text(encoding="utf-8"))))

    def governorates(self) -> list[str]:
        return list(self._governorates)

    def resolve_governorate(self, text: str) -> str | None:
        return self._aliases.get(normalize(text))

    def zones(self) -> list[Zone]:
        return list(self._zones.values())

    def get_zone(self, zone_id: str) -> Zone | None:
        return self._zones.get(zone_id)

    def get_lot(self, lot_id: str) -> Lot | None:
        return self._lots.get(lot_id)

    def lots_in_zone(self, zone_id: str) -> list[Lot]:
        return [lot for lot in self._lots.values() if lot.zone_id == zone_id]

    def search_lots(
        self,
        *,
        governorate: str | None = None,
        sector: str | None = None,
        min_area_m2: float | None = None,
        max_price_tnd: float | None = None,
        limit: int = 5,
    ) -> list[tuple[Lot, Zone]]:
        wanted_sector = normalize(sector) if sector else None
        matches: list[tuple[Lot, Zone]] = []
        for lot in self._lots.values():
            zone = self._zones[lot.zone_id]
            if lot.status != "available":
                continue
            if governorate and zone.governorate != governorate:
                continue
            if wanted_sector and not any(wanted_sector in normalize(s) for s in zone.sectors):
                continue
            if min_area_m2 is not None and lot.area_m2 < min_area_m2:
                continue
            if max_price_tnd is not None and lot.total_price_tnd > max_price_tnd:
                continue
            matches.append((lot, zone))
        matches.sort(key=lambda pair: pair[0].total_price_tnd)
        return matches[:limit]

    def procedures(self) -> list[Procedure]:
        return list(self._procedures.values())

    def get_procedure(self, procedure_id: str) -> Procedure | None:
        return self._procedures.get(procedure_id)

    def reserve_lot(self, lot_id: str) -> None:
        self._lots[lot_id] = self._lots[lot_id].model_copy(update={"status": "reserved"})
