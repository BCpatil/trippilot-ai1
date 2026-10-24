from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookingBase(BaseModel):
    trip_id: UUID
    customer_id: UUID
    booking_type: str = Field(min_length=1, max_length=60)
    supplier: str = Field(min_length=1, max_length=160)
    external_reference: str | None = Field(default=None, max_length=120)
    status: str = Field(default="draft", min_length=2, max_length=20)
    booked_date: date
    travel_date: date | None = None
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("booking_type", "supplier")
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


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    trip_id: UUID | None = None
    customer_id: UUID | None = None
    booking_type: str | None = Field(default=None, min_length=1, max_length=60)
    supplier: str | None = Field(default=None, min_length=1, max_length=160)
    external_reference: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, min_length=2, max_length=20)
    booked_date: date | None = None
    travel_date: date | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("booking_type", "supplier")
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


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    trip_id: UUID
    customer_id: UUID
    booking_type: str
    supplier: str
    external_reference: str | None
    status: str
    booked_date: date
    travel_date: date | None
    amount: Decimal
    currency: str
    notes: str | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class PaginatedBookingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[BookingResponse]
    count: int
