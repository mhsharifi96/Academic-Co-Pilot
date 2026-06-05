"""
Serve agent-generated artifacts (charts, screened spreadsheets, etc.) to the
browser so users can open/download them from the chat.

Only files under the project's known output directories are served, and the
resolved path is verified to stay inside those roots — this prevents path
traversal (e.g. ``?path=../../etc/passwd``).
"""

import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter()

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
):
    """
    Stream a generated file (chart PNG, screened XLSX, CSV, …) to the client.

    The frontend turns paths mentioned in the agent's replies into links to this
    endpoint so users can open or download the artifact directly.
    """
    abs_path = _resolve_safe(path)
    filename = os.path.basename(abs_path)
    disposition = "inline" if inline else "attachment"
    return FileResponse(
        abs_path,
        filename=filename,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )
