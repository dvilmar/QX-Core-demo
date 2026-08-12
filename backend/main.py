"""FastAPI entrypoint — CORS, router mount, background live-tick task."""

import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import live_tick_loop, router

app = FastAPI(title="Algo Trading Dashboard API (demo)", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def _start_background_tasks() -> None:
    asyncio.create_task(live_tick_loop())


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
