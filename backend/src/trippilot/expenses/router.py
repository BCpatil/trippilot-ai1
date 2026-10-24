from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership
from trippilot.db.session import get_db
from trippilot.expenses.schemas import (
    BudgetSummaryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)
from trippilot.models import Expense, Membership, Trip

router = APIRouter(prefix="/api/v1", tags=["expenses"])


def get_trip_in_scope(
    trip_id: UUID,
    membership: Membership,
    database: Session,
) -> Trip:
    trip = database.scalar(
        select(Trip).where(
            Trip.id == trip_id,
            Trip.organization_id == membership.organization_id,
        )
    )
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.get("/trips/{trip_id}/budget-summary", response_model=BudgetSummaryResponse)
def get_budget_summary(
    trip_id: UUID,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> BudgetSummaryResponse:
    trip = get_trip_in_scope(trip_id, membership, database)
    expenses = database.scalars(
        select(Expense).where(
            Expense.trip_id == trip_id,
            Expense.organization_id == membership.organization_id,
        )
    ).all()
    total = sum((expense.amount for expense in expenses), Decimal("0.00"))
    remaining = trip.budget_amount - total
    return BudgetSummaryResponse(
        trip_id=trip.id,
        budget_amount=float(trip.budget_amount),
        expenses_total=float(total),
        remaining_amount=float(remaining),
        currency=trip.currency,
    )


@router.get("/trips/{trip_id}/expenses")
def list_expenses(
    trip_id: UUID,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> list[ExpenseResponse]:
    get_trip_in_scope(trip_id, membership, database)
    expenses = database.scalars(
        select(Expense)
        .where(
            Expense.trip_id == trip_id,
            Expense.organization_id == membership.organization_id,
        )
        .order_by(Expense.incurred_date.desc())
    ).all()
    return [ExpenseResponse.model_validate(expense) for expense in expenses]


@router.post("/trips/{trip_id}/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    trip_id: UUID,
    payload: ExpenseCreate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ExpenseResponse:
    trip = get_trip_in_scope(trip_id, membership, database)
    expense = Expense(
        organization_id=membership.organization_id,
        trip_id=trip.id,
        category=payload.category,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        incurred_date=payload.incurred_date,
        notes=payload.notes,
        created_by=membership.user_id,
    )
    database.add(expense)
    database.commit()
    database.refresh(expense)
    return ExpenseResponse.model_validate(expense)


@router.patch("/trips/{trip_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    trip_id: UUID,
    expense_id: UUID,
    payload: ExpenseUpdate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> ExpenseResponse:
    get_trip_in_scope(trip_id, membership, database)
    expense = database.scalar(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.trip_id == trip_id,
            Expense.organization_id == membership.organization_id,
        )
    )
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None:
            setattr(expense, field, value)
    database.commit()
    database.refresh(expense)
    return ExpenseResponse.model_validate(expense)
