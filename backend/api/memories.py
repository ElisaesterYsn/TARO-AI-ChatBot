from fastapi import APIRouter, HTTPException

from services.memory_service import (
    get_all_memories,
    delete_memory,
    clear_all_memories,
)


router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("")
def list_memories():
    return get_all_memories()


@router.delete("/{memory_id}")
def remove_memory(memory_id: int):
    deleted = delete_memory(memory_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Memory not found"
        )

    return {"message": "Memory deleted"}


@router.delete("")
def remove_all_memories():
    clear_all_memories()

    return {"message": "All memories cleared"}
