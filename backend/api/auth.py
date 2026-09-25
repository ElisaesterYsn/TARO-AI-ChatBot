from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services.auth_service import (
    register_user,
    login_user,
    verify_token,
    delete_token,
    get_google_auth_url,
    exchange_google_code,
)


router = APIRouter(prefix="/auth", tags=["Auth"])

# Frontend URL — Google callback will redirect here with the token
FRONTEND_URL = "http://localhost:5173"


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    id: int
    username: str
    email: str
    token: str


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    try:
        user = register_user(request.username, request.email, request.password)
        return user
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    try:
        user = login_user(request.email, request.password)
        return user
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error))


@router.post("/logout")
def logout(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    if token:
        delete_token(token)
    return {"message": "Logged out"}


@router.get("/me")
def me(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ─── Google OAuth ─────────────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    """Redirects the browser to Google's consent screen."""
    import os
    if not os.environ.get("GOOGLE_CLIENT_ID"):
        raise HTTPException(
            status_code=503,
            detail="Google login is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    url = get_google_auth_url()
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(code: str = "", error: str = ""):
    """
    Google redirects here after the user approves.
    We exchange the code, get/create the user, then redirect to the
    frontend with the token in the URL fragment so JS can pick it up.
    """
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=google_denied")

    try:
        user = exchange_google_code(code)
        # Pass token to frontend via URL fragment — never lands in server logs
        return RedirectResponse(
            f"{FRONTEND_URL}/?token={user['token']}&username={user['username']}"
        )
    except Exception as e:
        print(f"[TARO Auth] Google callback error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/?auth_error=google_failed")
