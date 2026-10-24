from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseBase(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=220)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    incurred_date: date
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("category", "description")
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


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, min_length=1, max_length=220)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    incurred_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("category", "description")
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


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    trip_id: UUID
    category: str
    description: str
    amount: Decimal
    currency: str
    incurred_date: date
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class BudgetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trip_id: UUID
    budget_amount: float
    expenses_total: float
    remaining_amount: float
    currency: str
