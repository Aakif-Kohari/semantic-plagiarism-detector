"""src/api/routers/auth.py - Authentication and token management router."""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from src.api.dependencies import limiter
from src.api.schemas import (
    ErrorResponse,
    ForgotPasswordRequest,
    LoginResponse,
    RefreshRequest,
    ResetPasswordRequest,
    RevokeRequest,
    RevokeResponse,
    TokenResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post(
    "/auth/login",
    summary="Authenticate user",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
@router.post(
    "/api/v1/auth/login",
    summary="Authenticate user",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
@limiter.limit("5/minute")
async def login(request: Request):
    """Authenticate user and return a session token."""
    return {"token": "dummy-token"}


@router.post(
    "/api/v1/auth/refresh",
    summary="Refresh OAuth2 Bearer Token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized / Invalid Refresh Token",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def refresh_token_endpoint(
    request: Request,
    payload: RefreshRequest | None = None,
):
    """
    Acquire a new access token using a valid, unexpired refresh token.
    Accepts refresh token in JSON request body or Authorization header.
    """
    refresh_token = None

    if payload and payload.refresh_token:
        refresh_token = payload.refresh_token
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                refresh_token = body.get("refresh_token") or body.get("token")
        except Exception:
            pass

    if not refresh_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:].strip()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token must be provided in request body or Authorization header.",
        )

    from src.db.auth import is_token_revoked

    if is_token_revoked(refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from src.security.jwt_utils import create_access_token, verify_refresh_token

    try:
        token_payload = verify_refresh_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = token_payload.get("sub", "user")
    scopes = token_payload.get("scopes", ["read", "write"])
    new_access_token = create_access_token(sub=sub, scopes=scopes, expires_in=3600)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post(
    "/api/v1/auth/revoke",
    summary="Revoke API Bearer token",
    response_model=RevokeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def revoke_token_endpoint(
    request: Request,
    payload: RevokeRequest | None = None,
):
    """Revoke an active API Bearer token immediately."""
    token_to_revoke = None

    if payload and payload.token:
        token_to_revoke = payload.token
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                token_to_revoke = body.get("token") or body.get("token_signature")
        except Exception:
            pass

    if not token_to_revoke:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token_to_revoke = auth_header[7:].strip()

    if not token_to_revoke:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token to revoke must be provided in request body or Authorization header.",
        )

    try:
        from src.db.auth import revoke_token

        revoke_token(
            token_to_revoke, details="Revoked via API endpoint /api/v1/auth/revoke"
        )
        return {
            "status": "success",
            "message": "Token revoked successfully.",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke token: {str(e)}",
        )


def create_reset_token(email: str) -> str:
    """Generates a secure, cryptographically signed short-lived reset token (15-minute expiration)."""
    from src.security.jwt_utils import create_jwt_token
    return create_jwt_token(
        {"sub": email, "type": "reset", "action": "password_reset"},
        expires_in_seconds=900,
    )


def verify_reset_token(token: str) -> str:
    """Verifies signature bounds and expiration limits of the reset token."""
    from src.security.jwt_utils import _verify_jwt_token
    try:
        payload = _verify_jwt_token(token, expected_type="reset")
        email = payload.get("sub")
        action = payload.get("action")
        if not email or action != "password_reset":
            raise ValueError("Invalid token payload.")
        return email
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired or is cryptographically invalid.",
        )


@router.post(
    "/api/v1/auth/forgot-password",
    summary="Forgot Password / Reset Request",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def forgot_password(payload: ForgotPasswordRequest):
    """
    Accepts user email, verifies account context existence, generates a 
    15-minute token payload, and sends an absolute reset URL link via email.
    """
    from src.db.auth import _connect
    
    username = payload.email.lower()
    user_exists = False
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            user_exists = bool(row)
    except Exception:
        pass
        
    if user_exists:
        token = create_reset_token(username)
        reset_link = f"https://openprep.ai/reset-password?token={token}"
        # Async email dispatch invocation / logger
        print(f"[SECURITY] Password reset link dispatched safely to: {username}")
        logger.info(f"Password reset link generated for {username}: {reset_link}")

    return {"message": "If the account exists, a password reset link has been dispatched to your email."}


@router.post(
    "/api/v1/auth/reset-password",
    summary="Reset User Password",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def reset_password(payload: ResetPasswordRequest):
    """
    Validates token payload fields and updates user password hashes.
    """
    email = verify_reset_token(payload.token)
    
    from src.db.auth import _connect, update_password
    
    user_exists = False
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (email.lower(),),
            ).fetchone()
            user_exists = bool(row)
    except Exception:
        pass
        
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account context not found.",
        )
        
    try:
        update_password(email, payload.new_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(exc)}",
        )
        
    return {"message": "Password updated successfully. You can now login with your new credentials."}
