import os

from fastapi import Header, HTTPException, Request, WebSocket

import auth_session

API_KEY = os.getenv("DASHBOARD_API_KEY", "")


def _allowed(api_key: str | None, cookie: str | None) -> bool:
    if not API_KEY and not auth_session.login_configured():
        return True
    if API_KEY and api_key == API_KEY:
        return True
    return auth_session.login_configured() and auth_session.verify_token(cookie)


def require_auth(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    if not _allowed(x_api_key, request.cookies.get(auth_session.COOKIE_NAME)):
        raise HTTPException(status_code=401, detail="Invalid or missing credentials")


async def check_ws_auth(websocket: WebSocket) -> bool:
    key = websocket.query_params.get("api_key")
    if _allowed(key, websocket.cookies.get(auth_session.COOKIE_NAME)):
        return True
    await websocket.close(code=4401)
    return False
