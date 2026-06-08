import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas.ingestion import IngestionResponse, FileIngestionResult
from app.tools.ingestor import ingest_pdf
from app.core.sessions import session_manager
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.services.session_service import ensure_session

router = APIRouter()

# Root directory for uploads.  Each session gets its own subdirectory
# (``data/<session_id>/``) so files uploaded in different sessions never
# collide or overwrite each other.
UPLOAD_ROOT = "data"
if not os.path.exists(UPLOAD_ROOT):
    os.makedirs(UPLOAD_ROOT)


@router.post("/upload", response_model=IngestionResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload one or more files (PDF or CSV).

    - PDFs are automatically ingested into the vector database.
    - CSVs are saved to the session's upload directory for screening/analysis.

    All uploaded files are saved under ``data/<session_id>/`` and associated with
    that ``session_id`` so the chat agent can reference them.  Requires
    authentication; the session is created under / verified against the user.
    """
    # Resolve session and its dedicated upload directory.
    sid = session_id or str(uuid.uuid4())

    # Create or verify ownership of the session before writing any files.
    try:
        await ensure_session(db, current_user, sid)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Session not found.")

    upload_dir = os.path.join(UPLOAD_ROOT, sid)
    os.makedirs(upload_dir, exist_ok=True)

    # Validate every file first so we don't partially ingest
    for f in files:
        fname = f.filename.lower() if f.filename else ""
        if not (fname.endswith(".pdf") or fname.endswith(".csv")):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF and CSV files are allowed.  Rejected: '{f.filename}'",
            )

    results: List[FileIngestionResult] = []
    saved_paths: List[str] = []

    for f in files:
        # basename guards against path-traversal in the client-supplied name.
        safe_name = os.path.basename(f.filename or "unknown")
        file_path = os.path.join(upload_dir, safe_name)
        fname = safe_name

        try:
            # Save file locally
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved_paths.append(file_path)

            # Ingest PDFs into the vector store
            if fname.lower().endswith(".pdf"):
                ingestion_msg = ingest_pdf.invoke({"file_path": file_path})
                if "Error" in ingestion_msg:
                    results.append(FileIngestionResult(
                        filename=fname,
                        file_path=file_path,
                        status="error",
                        message=ingestion_msg,
                    ))
                else:
                    results.append(FileIngestionResult(
                        filename=fname,
                        file_path=file_path,
                        status="success",
                        message=ingestion_msg,
                    ))
            else:
                # CSV — just acknowledge
                results.append(FileIngestionResult(
                    filename=fname,
                    file_path=file_path,
                    status="success",
                    message=f"Successfully saved {fname} to {upload_dir}.",
                ))
        except Exception as e:
            # Clean up the file on disk if something went wrong
            if os.path.exists(file_path):
                os.remove(file_path)
            results.append(FileIngestionResult(
                filename=fname,
                file_path=file_path,
                status="error",
                message=f"Processing Error: {str(e)}",
            ))
        finally:
            f.file.close()

    # Associate all successfully saved files with the session
    await session_manager.add_files(
        sid,
        [r.file_path for r in results if r.status != "error"],
    )

    # Build a summary message
    success_count = sum(1 for r in results if r.status == "success")
    error_count = sum(1 for r in results if r.status == "error")
    summary = (
        f"Processed {len(results)} file(s): {success_count} succeeded"
        + (f", {error_count} failed." if error_count else ".")
    )

    return IngestionResponse(
        message=summary,
        session_id=sid,
        files=results,
    )
