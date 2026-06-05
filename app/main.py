from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import chat, ingestion, sessions, files
from app.core.checkpointer import build_checkpointer_cm
from app.agents.academic_agent import AcademicAgent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Open the conversation checkpointer (Postgres saver, or in-memory fallback),
    run its one-time table setup, build the single shared agent on top of it, and
    expose both on ``app.state`` for the request handlers.  Everything is torn
    down cleanly on shutdown.
    """
    cm = build_checkpointer_cm()
    async with cm as saver:
        # Creates the checkpoint tables if they don't exist (no-op in-memory).
        await saver.setup()

        app.state.checkpointer = saver
        app.state.agent = AcademicAgent(checkpointer=saver)
        yield
    # Saver / connection pool closed here by the context manager.


app = FastAPI(title="Academic Co-Pilot API", lifespan=lifespan)

# Allow the React dev server (Vite, port 5173) to call the API.
# Wide-open origins are acceptable for this local-first MVP.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(files.router, prefix="/api/v1", tags=["files"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Academic Co-Pilot API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
