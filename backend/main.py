from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.conversations import router as conversations_router
from api.memories import router as memories_router
from api.auth import router as auth_router
from database.db import init_db


app = FastAPI(title="TARO")


init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(memories_router)


@app.get("/")
def root():
    return {
        "message": "TARO is alive 🤖"
    }