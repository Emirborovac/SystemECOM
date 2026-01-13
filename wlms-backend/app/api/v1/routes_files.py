import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.file import File
from app.models.user import User
from app.services.storage_service import load_bytes

router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
def list_files(
    file_type: str | None = Query(default=None),
    created_after: str | None = Query(default=None),
    created_before: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    stmt = select(File).where(File.tenant_id == user.tenant_id)
    if user.client_id is not None:
        stmt = stmt.where(File.client_id == user.client_id)

    if file_type:
        stmt = stmt.where(File.file_type == file_type)

    def _parse_dt(v: str) -> datetime:
        # Accept RFC3339-ish string, tolerate trailing Z
        vv = v.replace("Z", "+00:00")
        dt = datetime.fromisoformat(vv)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    if created_after:
        stmt = stmt.where(File.created_at >= _parse_dt(created_after))
    if created_before:
        stmt = stmt.where(File.created_at <= _parse_dt(created_before))
    items = db.scalars(stmt).all()
    return [
        {
            "id": str(f.id),
            "file_type": f.file_type,
            "original_name": f.original_name,
            "mime_type": f.mime_type,
            "size_bytes": f.size_bytes,
            "created_at": f.created_at.isoformat(),
        }
        for f in items
    ]


@router.get("/{file_id}/download")
def download(file_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    try:
        fid = uuid.UUID(file_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    f = db.scalar(select(File).where(File.id == fid, File.tenant_id == user.tenant_id))
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if user.client_id is not None and f.client_id != user.client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    data = load_bytes(storage_provider=f.storage_provider, storage_key=f.storage_key)
    return Response(content=data, media_type=f.mime_type, headers={"Content-Disposition": f'attachment; filename="{f.original_name}"'})


