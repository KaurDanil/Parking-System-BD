import os
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user
from app.models import User


ADMIN_PHONE = os.getenv("ADMIN_PHONE", "000")


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that ensures current user is an admin.
    For simplicity, admin is a user with phone == ADMIN_PHONE.
    """
    if current_user.phone != ADMIN_PHONE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

