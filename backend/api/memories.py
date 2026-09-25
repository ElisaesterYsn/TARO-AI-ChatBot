from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user
from services.memory_service import (
    get_all_memories,
    delete_memory,
    clear_all_memories,
)


router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("")
def list_memories(current_user: dict = Depends(get_current_user)):
    return get_all_memories(current_user["id"])


@router.delete("/{memory_id}")
def remove_memory(
    memory_id: int,
    current_user: dict = Depends(get_current_user),
):
    deleted = delete_memory(memory_id, current_user["id"])

    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"message": "Memory deleted"}


@router.delete("")
def remove_all_memories(current_user: dict = Depends(get_current_user)):
    clear_all_memories(current_user["id"])
    return {"message": "All memories cleared"}
