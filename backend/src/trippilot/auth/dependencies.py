import hmac
from collections.abc import Callable
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from trippilot.auth.security import decode_access_token
from trippilot.db.session import get_db
from trippilot.models import Membership, User


def require_csrf(
    csrf_cookie: str | None = Cookie(default=None, alias="trip_pilot_csrf"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def get_current_user(
    session_cookie: str | None = Cookie(default=None, alias="trip_pilot_session"),
    database: Session = Depends(get_db),
) -> User:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    claims = decode_access_token(session_cookie)
    subject = claims.get("sub")
    try:
        user_id = UUID(str(subject))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required") from error
    user = database.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def get_current_membership(
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
    organization_id: UUID | None = Header(default=None, alias="X-Organization-ID"),
) -> Membership:
    query = select(Membership).where(Membership.user_id == user.id)
    if organization_id is not None:
        query = query.where(Membership.organization_id == organization_id)
    memberships = list(database.scalars(query).all())
    if organization_id is not None and not memberships:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization membership")
    if organization_id is None and len(memberships) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select an organization")
    return memberships[0]


def require_roles(*allowed_roles: str) -> Callable:
    def check_role(membership: Membership = Depends(get_current_membership)) -> Membership:
        if membership.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return membership

    return check_role
