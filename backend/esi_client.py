import collections
import collections.abc

# Monkey patch for pyswagger/esipy compatibility with Python 3.10+
collections.MutableMapping = collections.abc.MutableMapping
collections.Mapping = collections.abc.Mapping

from datetime import datetime, timedelta
from typing import Optional

import requests
from esipy import EsiApp, EsiClient, EsiSecurity

from backend.config import settings

# EVE SSO token endpoint (v2)
_EVE_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"

# Initialize EsiApp (loads the Swagger spec)
# In production, you might want to cache this spec locally to avoid fetching it on every restart
esi_app = EsiApp().get_latest_swagger

# Initialize EsiSecurity
esi_security = EsiSecurity(
    redirect_uri=settings.EVE_CALLBACK_URL,
    client_id=settings.EVE_CLIENT_ID,
    secret_key=settings.EVE_CLIENT_SECRET,
    headers={"User-Agent": "Lenny/1.0"},
)

# Initialize EsiClient
esi_client = EsiClient(security=esi_security, headers={"User-Agent": "Lenny/1.0"})


def refresh_tokens(refresh_token: str) -> dict:
    """
    Call EVE SSO to refresh tokens using the provided refresh token.
    Returns the token response dict on success, raises RuntimeError on failure.
    """
    if not refresh_token:
        raise RuntimeError("Missing refresh token")

    headers = {
        "User-Agent": "Lenny/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    auth = (settings.EVE_CLIENT_ID, settings.EVE_CLIENT_SECRET)

    resp = requests.post(_EVE_TOKEN_URL, headers=headers, data=data, auth=auth, timeout=10)

    try:
        rj = resp.json()
    except Exception:
        raise RuntimeError(f"Invalid token response: {resp.status_code} {resp.text}")

    if resp.status_code != 200:
        err = rj.get("error_description") or rj.get("error") or resp.text
        raise RuntimeError(f"Token refresh failed: {err}")

    return rj


async def ensure_valid_token(user, db_session) -> None:
    """
    Ensure the user's access token is valid. If expired (or about to expire),
    refresh it and persist the new tokens on the provided async DB session.

    `user` must be a SQLAlchemy user model instance attached to `db_session`.
    """
    # The token_expiry value in the DB is stored without tz in existing code,
    # so compare against naive utcnow for compatibility.
    now = datetime.utcnow()

    # If token_expiry is missing, consider it expired
    expiry = getattr(user, "token_expiry", None)
    if expiry is None or expiry <= now + timedelta(seconds=60):
        # Attempt refresh
        try:
            tokens = refresh_tokens(getattr(user, "refresh_token", None))
        except Exception as e:
            raise RuntimeError(
                f"Failed to refresh token for user {getattr(user, 'character_id', '?')}: {e}"
            )

        # Update user fields and commit
        user.access_token = tokens.get("access_token")
        # Some responses include a new refresh_token, others may not; only update if present
        if tokens.get("refresh_token"):
            user.refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in") or 0
        user.token_expiry = datetime.utcnow() + timedelta(seconds=int(expires_in))

        # Persist changes. `db_session` is expected to be an AsyncSession from the
        # application's dependency injection. Caller must pass a valid session.
        try:
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
        except Exception as e:
            # If commit fails, bubble up a clear error
            raise RuntimeError(f"Failed to persist refreshed token: {e}")


def auth_header_for_user(user) -> dict:
    """Return Authorization header for a user model instance."""
    token = getattr(user, "access_token", None)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}
