from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItineraryDayBase(BaseModel):
    day_date: date
    title: str = Field(min_length=1, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned


class ItineraryDayCreate(ItineraryDayBase):
    pass


class ItineraryDayUpdate(BaseModel):
    day_date: date | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned


class ItineraryItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(default="activity", max_length=40)
    start_time: str | None = Field(default=None, max_length=10)
    end_time: str | None = Field(default=None, max_length=10)
    estimated_cost: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source_label: str | None = Field(default=None, max_length=60)

    @field_validator("title", "category", "source_label")
    @classmethod
    def trim_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()


class ItineraryItemCreate(ItineraryItemBase):
    pass


class ItineraryItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=40)
    start_time: str | None = Field(default=None, max_length=10)
    end_time: str | None = Field(default=None, max_length=10)
    estimated_cost: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source_label: str | None = Field(default=None, max_length=60)

    @field_validator("title", "category", "source_label")
    @classmethod
    def trim_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()


class ItineraryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    itinerary_day_id: UUID
    organization_id: UUID
    title: str
    description: str | None
    category: str
    start_time: str | None
    end_time: str | None
    position: int
    estimated_cost: Decimal | None
    currency: str | None
    source_label: str | None
    created_at: datetime
    updated_at: datetime


class ItineraryDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    organization_id: UUID
    day_date: date
    title: str
    notes: str | None
    position: int
    created_at: datetime
    updated_at: datetime
    items: list[ItineraryItemResponse]


class ItineraryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    days: list[ItineraryDayResponse]
