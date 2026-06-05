from pydantic import BaseModel
from typing import List


class FileIngestionResult(BaseModel):
    filename: str
    file_path: str
    status: str = "success"
    message: str


class IngestionResponse(BaseModel):
    message: str
    session_id: str
    files: List[FileIngestionResult]
    status: str = "success"
