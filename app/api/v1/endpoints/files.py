"""
Serve agent-generated artifacts (charts, screened spreadsheets, etc.) to the
browser so users can open/download them from the chat.

Only files under the project's known output directories are served, and the
resolved path is verified to stay inside those roots — this prevents path
traversal (e.g. ``?path=../../etc/passwd``).
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import _user_from_token

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

# Directories the agent writes into and that are safe to expose read-only.
# ``data`` holds uploads + screened outputs; ``output_figures`` holds charts.
ALLOWED_ROOTS = ("data", "output_figures")


def _resolve_safe(path: str) -> str:
    """
    Resolve ``path`` against the project root and confirm it lives inside one of
    the allowed roots.  Raises HTTP 400/404 otherwise.
    """
    # Normalise and make absolute relative to the current working directory
    # (the project root, where ``data/`` and ``output_figures/`` live).
    requested = os.path.normpath(path).lstrip(os.sep)
    abs_path = os.path.abspath(requested)

    for root in ALLOWED_ROOTS:
        root_abs = os.path.abspath(root)
        # Ensure abs_path is root_abs itself or strictly within it.
        if abs_path == root_abs or abs_path.startswith(root_abs + os.sep):
            if not os.path.isfile(abs_path):
                raise HTTPException(status_code=404, detail="File not found.")
            return abs_path

    raise HTTPException(status_code=400, detail="Path is not in an allowed directory.")


@router.get("/download")
async def download_file(
    path: str = Query(..., description="Path under data/ or output_figures/"),
    inline: bool = Query(False, description="Render inline (e.g. images) vs attachment"),
    token: Optional[str] = Query(None, description="JWT, for <img>/link auth"),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream a generated file (chart PNG, screened XLSX, CSV, …) to the client.

    Requires authentication.  Because the browser cannot attach an
    ``Authorization`` header to ``<img src>`` or link navigation, the token may
    be supplied either in that header **or** as a ``?token=`` query param (the
    frontend uses the query param for inline images/links).
    """
    # Authenticate via header or query-param token.
    bearer_token = creds.credentials if creds else None
    await _user_from_token(bearer_token or token, db)

    abs_path = _resolve_safe(path)
    filename = os.path.basename(abs_path)
    disposition = "inline" if inline else "attachment"
    return FileResponse(
        abs_path,
        filename=filename,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )
