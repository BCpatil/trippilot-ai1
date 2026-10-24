from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership, require_csrf
from trippilot.customers.schemas import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    PaginatedCustomersResponse,
)
from trippilot.db.session import get_db
from trippilot.models import Customer, Membership

router = APIRouter(prefix="/api/v1", tags=["customers"])


@router.get("/customers", response_model=PaginatedCustomersResponse)
def list_customers(
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> PaginatedCustomersResponse:
    customers = database.scalars(
        select(Customer)
        .where(Customer.organization_id == membership.organization_id)
        .order_by(Customer.last_name, Customer.first_name)
    ).all()
    return PaginatedCustomersResponse(
        items=[CustomerResponse.model_validate(customer) for customer in customers],
        count=len(customers),
    )


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_customer(
    payload: CustomerCreate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> CustomerResponse:
    if payload.email is not None:
        existing = database.scalar(
            select(Customer.id)
            .where(
                Customer.organization_id == membership.organization_id,
                Customer.email.is_not(None),
                func.lower(Customer.email) == payload.email.lower(),
            )
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already exists")

    customer = Customer(
        organization_id=membership.organization_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        notes=payload.notes,
    )
    database.add(customer)
    database.commit()
    database.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> CustomerResponse:
    customer = database.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == membership.organization_id,
        )
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerResponse.model_validate(customer)


@router.patch(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_csrf)],
)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    membership: Membership = Depends(get_current_membership),
    database: Session = Depends(get_db),
) -> CustomerResponse:
    customer = database.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == membership.organization_id,
        )
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return CustomerResponse.model_validate(customer)

    if "email" in updates and updates["email"] is not None:
        existing = database.scalar(
            select(Customer.id)
            .where(
                Customer.organization_id == membership.organization_id,
                Customer.id != customer.id,
                Customer.email.is_not(None),
                func.lower(Customer.email) == updates["email"].lower(),
            )
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already exists")

    for field, value in updates.items():
        setattr(customer, field, value)

    database.commit()
    database.refresh(customer)
    return CustomerResponse.model_validate(customer)
