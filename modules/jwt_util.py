import os
from datetime import datetime, UTC, timedelta
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, Header

from modules.entity import user_db
from modules.logger import get_logger

load_dotenv()
logger = get_logger("JWT_UTILS")

# Get secret from environment with warning if using default
SECRET = os.getenv("JWT_SECRET")
if not SECRET:
    logger.warning(
        "JWT_SECRET not set in environment! Using default insecure secret. "
        "Please set JWT_SECRET in your .env file for production!"
    )
    SECRET = "superse345cret67"

# Token expiration time
TOKEN_EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS", "7"))


def create_jwt_token(user: dict) -> str:
    """
    Create a JWT token for a user.

    Args:
        user: User dictionary containing id, full_name, email, jwt_token_string

    Returns:
        str: Encoded JWT token
    """
    payload = {
        "id": user.get("id"),
        "name": user.get("full_name"),
        "email": user.get("email"),
        "jwt_token_string": user.get("jwt_token_string"),
        "exp": datetime.now(UTC) + timedelta(days=TOKEN_EXPIRY_DAYS),
        "iat": datetime.now(UTC),  # Issued at
        "type": "access",
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_jwt_token(token: str) -> dict:
    """
    Decode a JWT token and return the payload.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded payload

    Raises:
        HTTPException: If token is expired or invalid
    """
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired.")
        raise HTTPException(
            status_code=401, detail="Token has expired. Please login again."
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token.")


def get_user_from_token(token: str) -> dict:
    """
    Extract user info from JWT token and ensure token is still valid (not superseded).

    Args:
        token: JWT token string

    Returns:
        dict: User document from database

    Raises:
        HTTPException: If token is invalid, user not found, or token invalidated
    """
    payload = decode_jwt_token(token)

    # Verify token type
    if payload.get("type") != "access":
        logger.warning("Invalid token type")
        raise HTTPException(status_code=401, detail="Invalid token type.")

    user_id = payload.get("id")
    if not user_id:
        logger.warning("Token missing user ID")
        raise HTTPException(status_code=401, detail="Invalid token.")

    user = user_db.get_by_id(_id=user_id)
    if not user:
        logger.warning(f"User not found for token: {user_id}")
        raise HTTPException(status_code=401, detail="Invalid token.")

    if not user.get("is_active"):
        logger.warning(f"Inactive user attempted access: {user.get('email')}")
        raise HTTPException(status_code=401, detail="User account is not active.")

    # Check if the jwt_token_string in the token matches the one in the database
    # This allows for token invalidation (logout, password change, etc.)
    current_token_string = user.get("jwt_token_string")
    token_string_in_jwt = payload.get("jwt_token_string")

    if current_token_string != token_string_in_jwt:
        logger.warning(f"Token invalidated for user: {user.get('email')}")
        raise HTTPException(
            status_code=401, detail="Token has been invalidated. Please login again."
        )

    return user


def get_token_from_header(authorization: Optional[str] = None) -> str:
    """
    Extract token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        str: Extracted token

    Raises:
        HTTPException: If header is missing or malformed
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Authorization header must start with 'Bearer '."
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or not parts[1]:
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header format."
        )

    return parts[1]


def require_token(
    authorization: Optional[str] = Header(
        None, description="JWT token in 'Authorization: Bearer <token>' header format"
    ),
) -> dict:
    """
    FastAPI dependency to require and validate JWT token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        dict: Authenticated user document

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        logger.error("Authorization header is missing")
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    try:
        token = get_token_from_header(authorization)
        return get_user_from_token(token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in require_token: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed.")
