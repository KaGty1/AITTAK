import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api import router as admin_router
from app.audit import start_audit_writer, stop_audit_writer
from app.database import close_db, init_db
from app.proxy import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    writer_task = asyncio.create_task(start_audit_writer())
    yield
    await stop_audit_writer()
    writer_task.cancel()
    try:
        await writer_task
    except asyncio.CancelledError:
        pass
    await close_db()


app = FastAPI(title="AITTAK", lifespan=lifespan)

app.include_router(proxy_router)
app.include_router(admin_router, prefix="/admin/api")

_WEB_DIST = Path(__file__).parent.parent / "web" / "dist"
_NOT_BUILT = "web UI not built. Run: cd web && npm install && npm run build"


def _dist_file(path: str) -> Path | None:
    if not path:
        return None
    target = (_WEB_DIST / path).resolve()
    if target.is_file() and target.is_relative_to(_WEB_DIST.resolve()):
        return target
    return None


@app.get("/admin", response_class=HTMLResponse)
async def admin_redirect():
    return RedirectResponse("/")


if _WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_WEB_DIST / "assets"), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        if not (_WEB_DIST / "index.html").is_file():
            return HTMLResponse(_NOT_BUILT, status_code=503)
        return FileResponse(_WEB_DIST / "index.html")

    @app.get("/{path:path}", response_class=HTMLResponse)
    async def spa(path: str):
        if path.startswith(("v1/", "admin/api/")):
            return Response(content='{"error":"not found"}', status_code=404, media_type="application/json")
        if not (_WEB_DIST / "index.html").is_file():
            return HTMLResponse(_NOT_BUILT, status_code=503)
        target = _dist_file(path)
        return FileResponse(target) if target else FileResponse(_WEB_DIST / "index.html")
