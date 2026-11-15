from typing import Literal

from pydantic import BaseModel, computed_field

LotStatus = Literal["available", "reserved", "sold"]


class Governorate(BaseModel):
    name: str
    aliases: list[str] = []


class Zone(BaseModel):
    id: str
    name: str
    governorate: str
    area_ha: float
    sectors: list[str]
    infrastructure: list[str]
    regional_development_zone: bool
    lat: float
    lon: float


class Lot(BaseModel):
    id: str
    zone_id: str
    area_m2: float
    price_tnd_per_m2: float
    status: LotStatus

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_price_tnd(self) -> float:
        return round(self.area_m2 * self.price_tnd_per_m2, 2)


class Procedure(BaseModel):
    id: str
    title: str
    steps: list[str]
    documents: list[str]
    verified: bool = False


class SeedData(BaseModel):
    synthetic: bool
    note: str = ""
    governorates: list[Governorate]
    zones: list[Zone]
    lots: list[Lot]
    procedures: list[Procedure]


class RequestDraft(BaseModel):
    id: str
    lot_id: str
    applicant_name: str
    company_name: str | None
    activity: str
    phone: str | None
    status: Literal["awaiting_confirmation", "submitted"]
    tracking_number: str | None = None


class Dossier(BaseModel):
    tracking_number: str
    lot_id: str
    applicant_name: str
    status: str
    history: list[str]
