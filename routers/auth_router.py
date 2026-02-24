import re
from fastapi import APIRouter, Depends, status, Header, HTTPException
from fastapi.responses import JSONResponse

from models import user_model
from entity import user_db
from modules.jwt_util import create_jwt_token, require_token
from modules.logger import get_logger
from modules.utils import get_timestamp

auth_router = APIRouter()
logger = get_logger("AUTH_ROUTER")


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return (
            False,
            'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)]',
        )

    return True, ""


@auth_router.post(
    "/register",
    summary="Register a new user",
    description="Creates a new account with secure password requirements.",
    status_code=status.HTTP_201_CREATED,
    response_description="Registration successful",
    response_class=JSONResponse,
)
async def register(user: user_model.CreateUserInput):
    """
    Register a new user.

    Password requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Parameters:
        user: User registration data (full_name, email, password)

    Returns:
        dict: Success message and user data (without password)
    """
    try:
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Check if email already exists
        existing_user = user_db.get(filter={"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Prepare user data
        data = user.model_dump(exclude_unset=True)
        data["password"] = user_db.hashit(user.password)
        data["jwt_token_string"] = user_db.gen_string(
            length=32
        )  # For token invalidation

        # Create user document
        created_user = user_model.CreateUser(**data).model_dump()

        # Insert into database
        doc = user_db.insert(created_user)

        logger.info(f"New user registered: {user.email}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"msg": "success", "user": user_model.ReadUser(**doc).model_dump()},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=500, detail="Registration failed. Please try again."
        )


@auth_router.post(
    "/login",
    summary="Login a user",
    description="Authenticate a user and return a JWT token.",
    response_description="JWT token",
    response_class=JSONResponse,
)
async def login(login_data: user_model.LoginUser):
    """
    Login a user and return JWT token.

    Security note: Returns generic "Invalid credentials" message for both
    non-existent email and wrong password to prevent email enumeration attacks.

    Parameters:
        login_data: Login credentials (email, password)

    Returns:
        dict: JWT token and success message
    """
    try:
        # Find user by email
        user = user_db.get(filter={"email": login_data.email})

        # SECURITY: Use generic error message to prevent email enumeration
        # This prevents attackers from knowing if an email is registered
        if not user:
            logger.warning(f"Login attempt for non-existent email: {login_data.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        stored_password = user.get("password")
        if not stored_password or not user_db.verify_hash(
            login_data.password, stored_password
        ):
            logger.warning(f"Failed login attempt for user: {login_data.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check if user is active
        if not user.get("is_active", True):
            logger.warning(f"Inactive user login attempt: {login_data.email}")
            raise HTTPException(status_code=401, detail="Account is not active")

        # Generate JWT token
        jwt_token = create_jwt_token(user=user)

        logger.info(f"User logged in: {login_data.email}")

        return JSONResponse(
            status_code=200,
            content={
                "msg": "success",
                "token": jwt_token,
                "user": {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "full_name": user.get("full_name"),
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


@auth_router.post(
    "/change-password",
    summary="Change user password",
    description="Change the password for the authenticated user.",
    response_description="Password changed successfully",
    response_class=JSONResponse,
)
async def change_password(
    data: user_model.ChangePassword, current_user: dict = Depends(require_token)
):
    """
    Change the authenticated user's password.

    Requires authentication. User can only change their own password.
    All existing sessions will be invalidated after password change.

    Parameters:
        data: Change password data (current_password, new_password)
        current_user: Authenticated user (injected by dependency)

    Returns:
        dict: Success message
    """
    try:
        # Verify current password
        stored_password = current_user.get("password")
        if not stored_password or not user_db.verify_hash(
            data.current_password, stored_password
        ):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Validate new password strength
        is_valid, error_msg = validate_password_strength(data.new_password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Generate new jwt_token_string to invalidate all existing sessions
        new_token_string = user_db.gen_string(length=32)

        # Update password and token string
        user_db.update_one(
            filter={"id": current_user["id"]},
            update_data={
                "password": user_db.hashit(data.new_password),
                "jwt_token_string": new_token_string,
                "updated_at": get_timestamp(),
            },
        )

        logger.info(f"Password changed for user: {current_user.get('email')}")

        return JSONResponse(
            status_code=200,
            content={
                "msg": "success",
                "message": "Password changed successfully. Please login again with your new password.",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@auth_router.post(
    "/regenerate-token",
    summary="Regenerate JWT token",
    description="Generate a new JWT token for the authenticated user.",
    response_description="New JWT token",
    response_class=JSONResponse,
)
async def regenerate_token(current_user: dict = Depends(require_token)):
    """
    Regenerate JWT token for the authenticated user.

    Generates a new token with a new jwt_token_string, invalidating all other sessions.

    Parameters:
        current_user: Authenticated user (injected by dependency)

    Returns:
        dict: New JWT token
    """
    try:
        # Generate new token string to invalidate old sessions
        new_token_string = user_db.gen_string(length=32)

        # Update user with new token string
        user_db.update_one(
            filter={"id": current_user["id"]},
            update_data={"jwt_token_string": new_token_string},
        )

        # Get updated user and generate new token
        updated_user = user_db.get_by_id(_id=current_user["id"])
        new_jwt_token = create_jwt_token(updated_user)

        logger.info(f"Token regenerated for user: {current_user.get('email')}")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "msg": "success",
                "token": new_jwt_token,
                "message": "Token regenerated. All other sessions have been invalidated.",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token regeneration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate token")


@auth_router.post(
    "/logout",
    summary="Logout user",
    description="Logout the authenticated user by invalidating their JWT token.",
    response_description="Logout successful",
    response_class=JSONResponse,
)
async def logout(current_user: dict = Depends(require_token)):
    """
    Logout the authenticated user.

    Invalidates the current JWT token by updating the jwt_token_string.
    The user will need to login again to get a new token.

    Parameters:
        current_user: Authenticated user (injected by dependency)

    Returns:
        dict: Success message
    """
    try:
        # Invalidate token by changing jwt_token_string
        user_db.update_one(
            filter={"id": current_user["id"]},
            update_data={
                "jwt_token_string": user_db.gen_string(length=32),
                "updated_at": get_timestamp(),
            },
        )

        logger.info(f"User logged out: {current_user.get('email')}")

        return JSONResponse(
            status_code=200,
            content={
                "msg": "success",
                "message": "Logged out successfully. Your session has been invalidated.",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")
