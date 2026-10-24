from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TripBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    traveler_count: int = Field(ge=1, le=200)
    budget_amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    preferences: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="draft", min_length=2, max_length=20)

    @field_validator("title", "destination")
    @classmethod
    def trim_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, value: date, info):
        start = info.data.get("start_date")
        if start is not None and value < start:
            raise ValueError("end_date must be on or after start_date")
        return value


class TripCreate(TripBase):
    customer_id: UUID


class TripUpdate(BaseModel):
    customer_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    destination: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    traveler_count: int | None = Field(default=None, ge=1, le=200)
    budget_amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    preferences: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, min_length=2, max_length=20)

    @field_validator("title", "destination")
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
            return None
        return value.strip().upper()

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, value: date | None, info):
        if value is None:
            return value
        start = info.data.get("start_date")
        if start is not None and value < start:
            raise ValueError("end_date must be on or after start_date")
        return value


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    customer_id: UUID
    created_by: UUID
    title: str
    destination: str
    start_date: date
    end_date: date
    traveler_count: int
    budget_amount: Decimal
    currency: str
    preferences: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class PaginatedTripsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[TripResponse]
    count: int
