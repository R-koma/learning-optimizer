from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from api.dependencies import DB, CurrentUser
from repositories import note_repository
from schemas.note import NoteListResponse, NoteResponse, NoteUpdate

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("", response_model=NoteListResponse)
async def list_notes(current_user_id: CurrentUser, db: DB) -> NoteListResponse:
    records = await note_repository.find_by_user_id(db, current_user_id)
    return NoteListResponse(notes=[NoteResponse(**r) for r in records])


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: UUID, current_user_id: CurrentUser, db: DB) -> NoteResponse:
    record = await note_repository.find_by_id(db, note_id, current_user_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    return NoteResponse(**record)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: UUID, note_data: NoteUpdate, current_user_id: CurrentUser, db: DB) -> NoteResponse:
    update_data = note_data.model_dump(exclude_unset=True)
    record = await note_repository.update(db, note_id=note_id, user_id=current_user_id, **update_data)

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return NoteResponse(**record)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: UUID, current_user_id: CurrentUser, db: DB) -> None:
    success = await note_repository.delete(db, note_id, current_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
