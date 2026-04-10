from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

CabinClass = Literal["economy", "premium_economy", "business", "first"]
MaxStops = Literal["any", "0", "1", "2+"]
SearchMode = Literal["specific", "flexible"]
SortGoal = Literal["cheapest", "best_value", "best_nonstop"]


class FlightQuery(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: str | None = None
    cabin_class: CabinClass = "economy"
    max_stops: MaxStops = "any"

    @field_validator("origin", "destination")
    @classmethod
    def _airport_upper(cls, value: str) -> str:
        return value.upper().strip()


class DateQuery(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    trip_duration: int = Field(ge=1, le=31)
    weekend_only: bool = False
    cabin_class: CabinClass = "economy"
    max_stops: MaxStops = "any"

    @field_validator("origin", "destination")
    @classmethod
    def _airport_upper(cls, value: str) -> str:
        return value.upper().strip()


class FlightOption(BaseModel):
    provider: str
    searched_at: datetime = Field(default_factory=datetime.utcnow)
    origin: str
    destination: str
    departure_date: str
    return_date: str | None = None
    total_price: float
    currency: str
    total_duration_min: int
    stops: int = Field(ge=0)
    airlines: list[str]
    legs: list[dict[str, Any]]
    score: float | None = None
    tags: list[str]
    fingerprint: str


class DateOption(BaseModel):
    provider: str
    searched_at: datetime = Field(default_factory=datetime.utcnow)
    origin: str
    destination: str
    departure_date: str
    return_date: str | None = None
    trip_duration: int
    total_price: float
    currency: str
    score: float | None = None
    tags: list[str] = Field(default_factory=list)
    fingerprint: str


class Watcher(BaseModel):
    id: str
    name: str
    enabled: bool = True
    origin: str
    destination: str
    search_mode: SearchMode
    departure_date: str | None = None
    return_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    trip_duration: int | None = None
    weekend_only: bool = False
    cabin_class: CabinClass = "economy"
    max_stops: MaxStops = "any"
    max_price: float | None = None
    sort_goal: SortGoal = "best_value"
    notify_if_below_price: float | None = None
    notify_on_drop_percent: float | None = None
    notes: str | None = None

    @field_validator("origin", "destination")
    @classmethod
    def _airport_upper(cls, value: str) -> str:
        return value.upper().strip()


class WatcherRun(BaseModel):
    watcher_id: str
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    options_count: int = 0
    best_price: float | None = None
    status: Literal["ok", "error"] = "ok"
    message: str | None = None


class PriceSnapshot(BaseModel):
    watcher_id: str
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    departure_date: str
    return_date: str | None = None
    price: float
    currency: str
    duration_min: int
    stops: int
    airline_summary: str
    fingerprint: str


class DigestItem(BaseModel):
    watcher_id: str
    watcher_name: str
    headline: str
    body: str
    material_change: bool = False
