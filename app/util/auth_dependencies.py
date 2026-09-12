# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
import time
import uuid
from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from joserfc import errors, jwt
from sqlmodel import Session

from app.models.user import UserModel
from app.util.database import get_session
from app.util.settings import Settings

# Handle optional sentry import
try:
    if Settings().telemetry.enable:
        from sentry_sdk import set_user
    else:
        set_user = None
except Exception:
    set_user = None

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions"""

    pass


def authenticate_request(request: Request, token: Optional[str] = Cookie(None)) -> dict:
    """
    Unified authentication handler for both Discord and API key auth
    Returns JWT payload dict or raises AuthenticationError
    """
    # Check for API key in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer onboard_"):
        return _authenticate_api_key(auth_header)

    # Fallback to cookie-based JWT auth
    if token:
        return _authenticate_jwt_cookie(token)

    raise AuthenticationError("No valid authentication provided")


def _authenticate_api_key(auth_header: str) -> dict:
    """Validate API key and return equivalent JWT payload"""
    api_key = auth_header.replace("Bearer ", "")

    # Validate API key format
    if not api_key.startswith("onboard_live_"):
        raise AuthenticationError("Invalid API key format")

    # Check against configured keys
    configured_keys = Settings().api_keys or []
    key_config = None

    for config in configured_keys:
        if config.key == api_key:
            key_config = config
            break

    if not key_config:
        raise AuthenticationError("Invalid API key")

    logger.info(f"API key authentication successful: {key_config.name}")

    API_KEY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, Settings().http.domain)
    api_key_uuid = str(uuid.uuid5(API_KEY_NAMESPACE, api_key))
    logger.debug(f"API key UUID generated: {api_key_uuid}")

    return {
        "discord": None,
        "name": "API Key",
        "pfp": None,
        "id": api_key_uuid,
        "sudo": True,
        "is_full_member": True,
        "issued": time.time(),
        "infra_email": None,
        "auth_method": "api_key",
        "api_key": True,
        "api_key_name": key_config.name,
    }


def _authenticate_jwt_cookie(token: str) -> dict:
    """Validate JWT cookie and return payload"""
    try:
        user_jwt = jwt.decode(
            token,
            Settings().jwt.key_object,
            algorithms=[Settings().jwt.algorithm or "HS256"],
        )
        return user_jwt.claims
    except Exception as e:
        if isinstance(e, errors.BadSignatureError):
            raise AuthenticationError("Invalid token signature")
        else:
            raise AuthenticationError(f"Token validation failed: {e}")


# Header value that tells the browser to drop the session cookie. Mirrors what
# RedirectResponse.delete_cookie(key="token") emits on /logout.
_CLEAR_TOKEN_COOKIE = 'token=""; Max-Age=0; Path=/; HttpOnly; SameSite=lax'


def _reject(request: Request, detail: str, clear_cookie: bool = False) -> HTTPException:
    """
    Build the auth-failure response: 401 for API callers, otherwise a 302 back
    through Discord that returns the member to the page they asked for.
    """
    if request.headers.get("Authorization"):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    redir_jwt = sign_redirect_url(request.url.path)
    headers = {"Location": f"/discord/new?redir={redir_jwt}"}
    if clear_cookie:
        headers["Set-Cookie"] = _CLEAR_TOKEN_COOKIE
    return HTTPException(status_code=status.HTTP_302_FOUND, detail=detail, headers=headers)


def get_current_user(request: Request, token: Optional[str] = Cookie(None), session: Session = Depends(get_session)) -> dict:
    """
    FastAPI dependency to get current authenticated user
    Raises HTTPException on auth failure for web requests
    """
    try:
        user_jwt = authenticate_request(request, token)
    except AuthenticationError as e:
        # API callers get a 401 with the reason; browsers get sent through Discord.
        raise _reject(request, str(e) if request.headers.get("Authorization") else "Authentication required")

    # Session timeout check (skip for API keys)
    if not user_jwt.get("api_key", False):
        creation_date = user_jwt.get("issued", -1)
        if time.time() > creation_date + Settings().jwt.lifetime_user:
            raise _reject(request, "Session expired")

        # A signed JWT can outlive its user: the admin Discord-migration tool
        # deletes the temporary account it merges away, but the member's browser
        # keeps the cookie for that id for up to jwt.lifetime_user. Bounce them
        # through Discord so they land in the surviving account instead of
        # hitting a None user on every page.
        try:
            user_id = uuid.UUID(str(user_jwt.get("id")))
        except ValueError:
            user_id = None
        if user_id is None or session.get(UserModel, user_id) is None:
            logger.info("Rejecting JWT for user %s: no such user in the database", user_jwt.get("id"))
            raise _reject(request, "Account no longer exists", clear_cookie=True)

    # Set Sentry user context if enabled
    if Settings().telemetry.enable and set_user is not None:
        set_user({"id": user_jwt["id"]})

    return user_jwt


def get_current_member(current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency to ensure user is at least a member
    All authenticated users are considered members
    """
    return current_user


def get_current_admin(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency to ensure user has admin privileges
    """
    if not current_user.get("sudo", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Additional session timeout checks for non-API-key admin sessions
    if not current_user.get("api_key", False):
        creation_date = current_user.get("issued", -1)
        if time.time() > creation_date + Settings().jwt.lifetime_sudo:
            if request.headers.get("Authorization"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session expired")
            else:
                raise HTTPException(status_code=status.HTTP_302_FOUND, detail="Admin session expired - please re-authenticate", headers={"Location": f"/discord/new?redir={request.url.path}"})

    return current_user


CurrentUser = Annotated[dict, Depends(get_current_user)]
CurrentMember = Annotated[dict, Depends(get_current_member)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]


class Authentication:
    """
    Generate JWT token for user authentication
    """

    @staticmethod
    def create_jwt(user):
        """Keep existing JWT creation logic unchanged"""

        # Handle cases where discord relation might not be loaded
        discord_username = "Unknown"
        discord_avatar = None

        if hasattr(user, "discord") and user.discord:
            discord_username = user.discord.username
            discord_avatar = user.discord.avatar

        jwtData = {
            "discord": user.discord_id,
            "name": discord_username,
            "pfp": discord_avatar,
            "id": str(user.id),
            "sudo": user.sudo,
            "is_full_member": user.is_full_member,
            "issued": time.time(),
            "infra_email": user.infra_email,
            "auth_method": "discord",
            "api_key": False,
        }

        try:
            bearer = jwt.encode(
                {"alg": Settings().jwt.algorithm},
                jwtData,
                Settings().jwt.key_object,
            )
        except Exception as encode_error:
            logger.error(f"JWT encode error: {encode_error}")
            raise ValueError(f"Failed to encode JWT: {encode_error}")
        return bearer


def sign_redirect_url(url: str) -> str:
    """
    Sign a redirect URL to prevent tampering (CWE-601 mitigation).

    Args:
        url: The redirect URL to sign

    Returns:
        A signed token representing the URL
    """

    # Create a JWT payload with the URL and expiration
    payload = {
        "redirect_url": url,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,  # 5 minute expiration
        "purpose": "redirect",
    }

    try:
        token = jwt.encode(
            {"alg": Settings().jwt.algorithm},
            payload,
            Settings().jwt.redir_key,
        )
        return token
    except Exception as e:
        logger.error(f"Failed to sign redirect URL: {e}")
        raise ValueError("Failed to sign redirect URL")


def verify_redirect_url(signed_url: str) -> str:
    """
    Verify a signed redirect URL and extract the original URL.

    Args:
        signed_url: The signed URL token

    Returns:
        The original URL if valid, otherwise "/join/2"
    """

    try:
        decoded = jwt.decode(
            signed_url,
            Settings().jwt.redir_key,
            algorithms=[Settings().jwt.algorithm or "HS256"],
        )

        payload = decoded.claims

        # Verify this is a redirect token
        if payload.get("purpose") != "redirect":
            logger.warning("Invalid token purpose for redirect")
            return "/join/2"

        redirect_url = payload.get("redirect_url", "/join/2")

        # Basic sanity check - must be relative URL
        if redirect_url.startswith("/") and not redirect_url.startswith("//"):
            return redirect_url
        else:
            logger.warning(f"Invalid redirect URL format: {redirect_url}")
            return "/join/2"

    except Exception as e:
        logger.warning(f"Failed to verify redirect URL: {e}")
        return "/join/2"
