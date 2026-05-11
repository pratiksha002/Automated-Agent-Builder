from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"

# Routes that don't require a token
PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
}


def verify_token(request: Request) -> dict:
    """
    Verifies the Bearer JWT on the incoming request.
    Returns the decoded payload if valid.
    Raises 401 if missing, malformed, or expired.
    Skips verification for public paths.
    """
    if request.url.path in PUBLIC_PATHS:
        return {}

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )