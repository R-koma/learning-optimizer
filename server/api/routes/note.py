from fastapi import APIRouter, Depends

from api.dependencies import get_current_user

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("")
async def list_notes(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id, "notes": []}
