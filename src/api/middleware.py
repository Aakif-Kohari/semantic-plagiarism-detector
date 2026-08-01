import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# auto_error=False prevents FastAPI from automatically returning 403 when the header is missing,
# allowing us to manually return 401 with the correct message.
security = HTTPBearer(auto_error=False)

PUBLIC_PATHS = {
    "/health",
    "/healthz",
    "/metrics",
    "/metrics/json",
    "/api/v1/auth/login",
    "/api/v1/version",
    "/docs",
    "/redoc",
    "/openapi.json"
}

def get_expected_bearer_token() -> str:
    """Retrieve the API Bearer Token from environment variable or default fallback."""
    return os.getenv("API_BEARER_TOKEN", "dev-bearer-token")

async def verify_bearer_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Validate incoming Bearer token against configured secret.
    Excludes OPTIONS requests and public endpoints.
    """
    if request.method == "OPTIONS":
        return None

    if request.url.path in PUBLIC_PATHS:
        return None

    expected_token = get_expected_bearer_token()
    if not credentials or credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
