import re
import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from trippilot.auth.dependencies import get_current_membership, get_current_user, require_csrf
from trippilot.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    MembershipResponse,
    RegisterRequest,
)
from trippilot.auth.security import create_access_token, hash_password, verify_password
from trippilot.core.config import get_settings
from trippilot.db.session import get_db
from trippilot.models import Membership, Organization, User

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
SESSION_COOKIE = "trip_pilot_session"
CSRF_COOKIE = "trip_pilot_csrf"


def set_session_cookies(response: Response, user_id: str, csrf_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_access_token(user_id),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=settings.access_token_minutes * 60,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def organization_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:120] or "travel-team"
    return f"{base}-{uuid4().hex[:8]}"


@router.get("/csrf")
def issue_csrf_token(response: Response) -> dict[str, str]:
    csrf_token = secrets.token_urlsafe(32)
    settings = get_settings()
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=settings.access_token_minutes * 60,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return {"csrf_token": csrf_token}


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def register(
    payload: RegisterRequest,
    response: Response,
    database: Session = Depends(get_db),
) -> dict[str, str]:
    existing = database.scalar(select(User.id).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to create this account")

    user = User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    organization = Organization(name=payload.organization_name, slug=organization_slug(payload.organization_name))
    database.add_all([user, organization])
    try:
        database.flush()
        database.add(Membership(user_id=user.id, organization_id=organization.id, role="owner"))
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to create this account") from error

    csrf_token = secrets.token_urlsafe(32)
    set_session_cookies(response, str(user.id), csrf_token)
    return {"status": "registered", "csrf_token": csrf_token}


@router.post("/login", dependencies=[Depends(require_csrf)])
def login(
    payload: LoginRequest,
    response: Response,
    database: Session = Depends(get_db),
) -> dict[str, str]:
    user = database.scalar(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    csrf_token = secrets.token_urlsafe(32)
    set_session_cookies(response, str(user.id), csrf_token)
    return {"status": "authenticated", "csrf_token": csrf_token}


@router.get("/organizations", response_model=list[MembershipResponse])
def list_user_organizations(
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> list[MembershipResponse]:
    memberships = database.scalars(
        select(Membership)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at, Membership.organization_id)
    ).all()
    return [
        MembershipResponse(
            organization_id=membership.organization_id,
            organization_name=membership.organization.name,
            role=membership.role,
        )
        for membership in memberships
    ]


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"status": "signed_out"}


@router.get("/me", response_model=CurrentUserResponse)
def current_user(membership: Membership = Depends(get_current_membership)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=membership.user.id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        organization_id=membership.organization.id,
        organization_name=membership.organization.name,
        role=membership.role,
    )
