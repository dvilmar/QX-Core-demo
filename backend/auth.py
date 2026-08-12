"""Optional API-key auth middleware — same pattern as the private version of
this project, kept here to show the pattern even though the demo ships with
no key configured (open) by default."""

import os

from fastapi import Header, HTTPException, WebSocket

API_KEY = os.getenv("DASHBOARD_API_KEY", "")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not API_KEY:
        return  # auth disabled unless an API key is explicitly configured
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def check_ws_api_key(websocket: WebSocket) -> bool:
    if not API_KEY:
        return True
    key = websocket.query_params.get("api_key")
    if key != API_KEY:
        await websocket.close(code=4401)
        return False
    return True
