from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from pydantic import BaseModel

import auth_session as session

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response) -> dict:
    ip = request.client.host if request.client else "unknown"
    if session.is_rate_limited(ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try again later")
    if not session.check_credentials(body.username, body.password):
        session.record_failure(ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    session.clear_failures(ip)
    response.set_cookie(
        session.COOKIE_NAME,
        session.create_token(body.username),
        max_age=session.TTL_S,
        httponly=True,
        secure=session.cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(session.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/verify")
async def verify(qx_session: str | None = Cookie(default=None)) -> dict:
    if session.login_configured() and not session.verify_token(qx_session):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return {"ok": True}
