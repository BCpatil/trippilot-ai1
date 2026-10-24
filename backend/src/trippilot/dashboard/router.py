from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership
from trippilot.dashboard.schemas import (
    BookingStatusCount,
    BookingStatusResponse,
    CurrencyTotal,
    DashboardSummaryResponse,
    RevenuePoint,
    RevenueResponse,
)
from trippilot.db.session import get_db
from trippilot.models import Booking, Customer, Membership, Trip

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
BOOKING_STATUSES = ("draft", "confirmed", "tentative", "cancelled")


def resolve_date_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    today = date.today()
    resolved_end = end_date or today
    resolved_start = start_date or resolved_end - timedelta(days=29)
    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date",
        )
    return resolved_start, resolved_end


def date_range_parameters(
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> tuple[date, date]:
    return resolve_date_range(start_date, end_date)


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    date_range: Annotated[tuple[date, date], Depends(date_range_parameters)],
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    start_date, end_date = date_range
    organization_id = membership.organization_id
    active_customer_count = database.scalar(
        select(func.count(Customer.id)).where(
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
    ) or 0
    upcoming_trip_count = database.scalar(
        select(func.count(Trip.id)).where(
            Trip.organization_id == organization_id,
            Trip.start_date >= date.today(),
            Trip.status.not_in(("cancelled", "completed")),
        )
    ) or 0
    booking_rows = database.execute(
        select(Booking.currency, func.sum(Booking.amount), func.count(Booking.id))
        .where(
            Booking.organization_id == organization_id,
            Booking.booked_date.between(start_date, end_date),
            Booking.status != "cancelled",
        )
        .group_by(Booking.currency)
        .order_by(Booking.currency)
    ).all()
    return DashboardSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        active_customer_count=active_customer_count,
        upcoming_trip_count=upcoming_trip_count,
        booking_count=sum(int(row[2]) for row in booking_rows),
        booking_value_by_currency=[
            CurrencyTotal(currency=row[0], amount=row[1]) for row in booking_rows
        ],
    )


@router.get("/revenue", response_model=RevenueResponse)
def get_booking_value_by_day(
    date_range: Annotated[tuple[date, date], Depends(date_range_parameters)],
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> RevenueResponse:
    start_date, end_date = date_range
    rows = database.execute(
        select(
            Booking.booked_date,
            Booking.currency,
            func.count(Booking.id),
            func.sum(Booking.amount),
        )
        .where(
            Booking.organization_id == membership.organization_id,
            Booking.booked_date.between(start_date, end_date),
            Booking.status != "cancelled",
        )
        .group_by(Booking.booked_date, Booking.currency)
        .order_by(Booking.booked_date, Booking.currency)
    ).all()
    return RevenueResponse(
        start_date=start_date,
        end_date=end_date,
        items=[
            RevenuePoint(
                booked_date=row[0],
                currency=row[1],
                booking_count=int(row[2]),
                booking_value=row[3],
            )
            for row in rows
        ],
    )


@router.get("/booking-status", response_model=BookingStatusResponse)
def get_booking_status_counts(
    date_range: Annotated[tuple[date, date], Depends(date_range_parameters)],
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> BookingStatusResponse:
    start_date, end_date = date_range
    rows = database.execute(
        select(Booking.status, func.count(Booking.id))
        .where(
            Booking.organization_id == membership.organization_id,
            Booking.booked_date.between(start_date, end_date),
        )
        .group_by(Booking.status)
    ).all()
    counts = {row[0]: int(row[1]) for row in rows}
    return BookingStatusResponse(
        start_date=start_date,
        end_date=end_date,
        items=[BookingStatusCount(status=booking_status, count=counts.get(booking_status, 0)) for booking_status in BOOKING_STATUSES],
    )