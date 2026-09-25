import hashlib
import hmac
import os
import secrets
import urllib.parse
import urllib.request
import json

from database.db import get_connection


# ─── Password hashing ─────────────────────────────────────────────────────────

def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"{salt.hex()}:{key.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


# ─── Token storage ────────────────────────────────────────────────────────────

def _create_token(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO sessions (user_id, token) VALUES (?, ?)",
        (user_id, token),
    )
    connection.commit()
    connection.close()
    return token


def verify_token(token: str) -> dict | None:
    if not token:
        return None
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT u.id, u.username, u.email, u.avatar
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    )
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def delete_token(token: str):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    connection.commit()
    connection.close()


# ─── Email / password ─────────────────────────────────────────────────────────

def register_user(username: str, email: str, password: str) -> dict:
    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        raise ValueError("All fields are required.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        connection.close()
        raise ValueError("An account with that email already exists.")

    password_hash = _hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash),
    )
    user_id = cursor.lastrowid
    connection.commit()
    connection.close()

    token = _create_token(user_id)
    return {"id": user_id, "username": username, "email": email, "token": token}


def login_user(email: str, password: str) -> dict:
    email = email.strip().lower()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, username, email, password_hash FROM users WHERE email = ?",
        (email,),
    )
    row = cursor.fetchone()
    connection.close()

    if not row or not row["password_hash"]:
        raise ValueError("Invalid email or password.")
    if not _verify_password(password, row["password_hash"]):
        raise ValueError("Invalid email or password.")

    token = _create_token(row["id"])
    return {"id": row["id"], "username": row["username"], "email": row["email"], "token": token}


# ─── Google OAuth ─────────────────────────────────────────────────────────────
# Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment variables.
# Set them in your shell before starting the backend:
#   export GOOGLE_CLIENT_ID="your-client-id"
#   export GOOGLE_CLIENT_SECRET="your-client-secret"

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8001/auth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url(state: str = "") -> str:
    """Returns the Google OAuth2 authorization URL to redirect the user to."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_google_code(code: str) -> dict:
    """
    Exchanges the OAuth2 code for tokens, fetches user info,
    and upserts the user. Returns {"id", "username", "email", "token"}.
    """
    # Exchange code for access token
    token_data = urllib.parse.urlencode({
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        token_response = json.loads(resp.read())

    access_token = token_response.get("access_token")
    if not access_token:
        raise ValueError("Failed to obtain access token from Google.")

    # Fetch user info
    info_req = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    with urllib.request.urlopen(info_req, timeout=10) as resp:
        user_info = json.loads(resp.read())

    google_id = user_info.get("sub")
    email = user_info.get("email", "").lower()
    name = user_info.get("name") or email.split("@")[0]
    avatar = user_info.get("picture", "")

    if not google_id or not email:
        raise ValueError("Could not retrieve account info from Google.")

    # Upsert user — find by google_id or email
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, username FROM users WHERE google_id = ?", (google_id,))
    row = cursor.fetchone()

    if row:
        # Update avatar in case it changed
        cursor.execute(
            "UPDATE users SET avatar = ? WHERE id = ?",
            (avatar, row["id"]),
        )
        user_id = row["id"]
        username = row["username"]
    else:
        # Check if email already registered (password account — link it)
        cursor.execute("SELECT id, username FROM users WHERE email = ?", (email,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE users SET google_id = ?, avatar = ? WHERE id = ?",
                (google_id, avatar, existing["id"]),
            )
            user_id = existing["id"]
            username = existing["username"]
        else:
            cursor.execute(
                "INSERT INTO users (username, email, google_id, avatar) VALUES (?, ?, ?, ?)",
                (name, email, google_id, avatar),
            )
            user_id = cursor.lastrowid
            username = name

    connection.commit()
    connection.close()

    token = _create_token(user_id)
    return {"id": user_id, "username": username, "email": email, "token": token}
