from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse

from models import user_model
from modules.entity import user_db
from modules.jwt_util import require_token
from modules.logger import get_logger

user_router = APIRouter()
logger = get_logger("USER_ROUTER")


# Get current customer info
@user_router.get(
    "/me",
    response_model=user_model.ReadUser,
    summary="Get current customer info",
    description="Get the authenticated customer's information.",
    response_description="Customer info",
    response_class=JSONResponse,
)
async def get_me(user=Depends(require_token)):
    """
    Get current authenticated customer's info.

    Parameters:
        user (dict): Injected by dependency.

    Returns:
        CustomerOut: Customer info.
    """
    try:
        user_data = user_model.ReadUser(**user)
        return JSONResponse(user_data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"User not found: {e}")


# Update current customer info
@user_router.patch(
    "/me",
    summary="Update current customer info",
    description="Update the authenticated customer's information or password.",
    response_description="Update successful",
)
async def update_me(
    update: user_model.UpdateUser,
    user=Depends(require_token),
):
    """
    Update current authenticated customer's info or password.

    Parameters:
        update (CustomerUpdate): Update data.
        user (dict): Injected by dependency.

    Returns:
        dict: Success message.
    """
    update_data = update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    if "password" in update_data:
        update_data["password"] = user_db.hashit(update_data["password"])
    try:
        if user_db.update_one(filter={"id": user["id"]}, update_data=update_data):
            return {"msg": "Updated"}
        else:
            raise HTTPException(status_code=400, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Delete current customer
@user_router.delete(
    "/me",
    summary="Delete current customer",
    description="Delete the authenticated customer's account.NOTE: This will delete all the sessions and chat history for the user.",
    response_description="Delete successful",
    response_class=JSONResponse,
)
async def delete_me(_user=Depends(require_token)):
    """
    Delete current authenticated customer.

    Parameters:
        _user (dict): Injected by dependency.

    Returns:
        dict: Success message.
    """
    try:
        if user_db.delete_one(filter={"id": _user["id"]}):
            return JSONResponse({"msg": "Deleted"}, status_code=status.HTTP_200_OK)
        else:
            raise HTTPException(status_code=400, detail="User not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
