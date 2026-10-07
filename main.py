from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.api.routes import router
from app.auth import COOKIE_NAME, auth_enabled, expected_token, valid_token
from app.config import settings
from app.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description="Personal evidence-first stock intelligence dashboard: SEC, market, X, news, clustering and signal scoring.",
)
app.include_router(router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

PUBLIC_PATHS = {"/login", "/api/auth/login", "/api/v1/health"}


@app.middleware("http")
async def personal_access_guard(request: Request, call_next):
    path = request.url.path
    if not auth_enabled() or path in PUBLIC_PATHS or path.startswith("/static/"):
        return await call_next(request)

    if valid_token(request.cookies.get(COOKIE_NAME)):
        return await call_next(request)

    if path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


class LoginBody(BaseModel):
    password: str


@app.get("/login", include_in_schema=False)
def login_page():
    if not auth_enabled():
        return RedirectResponse("/dashboard", status_code=303)
    return FileResponse(static_dir / "login.html")


@app.post("/api/auth/login", include_in_schema=False)
def login(body: LoginBody):
    if not auth_enabled():
        return {"ok": True}
    if not hmac_compare(body.password, settings.app_password or ""):
        return JSONResponse({"detail": "Incorrect password"}, status_code=401)
    response = JSONResponse({"ok": True})
    response.set_cookie(
        COOKIE_NAME,
        expected_token(),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


def hmac_compare(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@app.post("/api/auth/logout", include_in_schema=False)
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(static_dir / "index.html")
