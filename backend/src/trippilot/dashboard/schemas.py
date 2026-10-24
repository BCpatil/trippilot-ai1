from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CurrencyTotal(BaseModel):
    currency: str
    amount: Decimal


class DashboardSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    active_customer_count: int
    upcoming_trip_count: int
    booking_count: int
    booking_value_by_currency: list[CurrencyTotal]


class RevenuePoint(BaseModel):
    booked_date: date
    currency: str
    booking_count: int
    booking_value: Decimal


class RevenueResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[RevenuePoint]


class BookingStatusCount(BaseModel):
    status: str
    count: int


class BookingStatusResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[BookingStatusCount]