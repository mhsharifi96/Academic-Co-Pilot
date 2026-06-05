import os
import pandas as pd
from langchain_core.tools import tool
from app.core.sessions import session_manager


@tool
def get_csv_info(csv_path: str) -> str:
    """
    Reads a CSV file and returns its structure: column names, data types,
    row count, column count, and a preview of the first 5 rows.

    Always use this tool BEFORE writing analytics code against a CSV so you
    know the exact column names and data types.

    Args:
        csv_path: Absolute or relative path to the CSV file.
    """
    if not os.path.exists(csv_path):
        return f"Error: File not found at '{csv_path}'."

    try:
        df = pd.read_csv(csv_path)
        buf = []
        buf.append(f"File: {csv_path}")
        buf.append(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        buf.append(f"Columns (name → dtype):")
        for col in df.columns:
            buf.append(f"  • {col}  →  {df[col].dtype}")
        buf.append(f"\nFirst 5 rows:")
        buf.append(df.head(5).to_string(index=False))
        return "\n".join(buf)
    except Exception as e:
        return f"Error reading CSV: {str(e)}"


@tool
def list_session_files(session_id: str) -> str:
    """
    Lists all files that have been uploaded and are available in the current
    user session.  Use this when the user asks what files or data are available.

    Args:
        session_id: The current session ID (available in your system prompt).
    """
    files = session_manager.sync_get_files(session_id)
    if not files:
        return "No files have been uploaded in this session yet. Upload PDFs or CSVs first."

    buf = [f"Files available in session {session_id}:"]
    for i, f in enumerate(files, 1):
        buf.append(f"  {i}. {f}")
    return "\n".join(buf)
