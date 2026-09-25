from fastapi import Header, HTTPException
from services.auth_service import verify_token


def get_current_user(authorization: str = Header(default="")) -> dict:
    """
    FastAPI dependency — extracts and validates the Bearer token.
    Returns the user dict {"id", "username", "email"} or raises 401.
    """
    token = authorization.removeprefix("Bearer ").strip()
    user = verify_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user
