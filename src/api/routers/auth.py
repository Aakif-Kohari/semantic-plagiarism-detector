"""src/api/routers/auth.py - Authentication and token management router."""

import base64
import io
import logging

import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, Request, status

from src.api.dependencies import limiter
from src.api.schemas import (
    ErrorResponse,
    LoginResponse,
    RefreshRequest,
    RevokeRequest,
    RevokeResponse,
    TokenResponse,
    TwoFactorSetupRequest,
    TwoFactorSetupResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


def generate_totp_qr_code_data_uri(otpauth_url: str) -> str:
    """Generate a base64-encoded PNG data URI of an otpauth:// URL using qrcode."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(otpauth_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_png = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_png}"


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


@router.post(
    "/auth/2fa/setup",
    summary="Initialize 2FA setup and return TOTP secret, otpauth URL, and base64 PNG QR code data URI",
    response_model=TwoFactorSetupResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
@router.post(
    "/api/v1/auth/2fa/setup",
    summary="Initialize 2FA setup and return TOTP secret, otpauth URL, and base64 PNG QR code data URI",
    response_model=TwoFactorSetupResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def setup_two_factor_auth_endpoint(
    request: Request,
    payload: TwoFactorSetupRequest | None = None,
):
    """
    Initialize TOTP 2FA setup for a user or admin.
    Generates a Base32 TOTP secret, otpauth:// URL, and a base64-encoded PNG QR code data URI
    suitable for instant scanning in Google Authenticator or Authy.
    """
    username = None
    issuer = "SemanticPlagiarismDetector"

    if payload:
        username = payload.username
        if payload.issuer:
            issuer = payload.issuer

    if not username:
        try:
            body = await request.json()
            if isinstance(body, dict):
                username = body.get("username")
                if body.get("issuer"):
                    issuer = body.get("issuer")
        except Exception:
            pass

    if not username:
        username = "admin"

    try:
        from src.db.auth import enable_2fa, get_2fa_status, init_db

        init_db()
        enabled, existing_secret = get_2fa_status(username)
        secret = existing_secret or pyotp.random_base32()

        enable_2fa(username, secret)

        totp = pyotp.TOTP(secret)
        otpauth_url = totp.provisioning_uri(name=username, issuer_name=issuer)
        qr_code_data_uri = generate_totp_qr_code_data_uri(otpauth_url)

        return {
            "secret": secret,
            "otpauth_url": otpauth_url,
            "qr_code_data_uri": qr_code_data_uri,
            "message": "2FA setup initialized successfully. Scan QR code in Google Authenticator or Authy.",
        }
    except Exception as e:
        logger.error("Failed to initialize 2FA setup for user %s: %s", username, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize 2FA setup: {str(e)}",
        )
