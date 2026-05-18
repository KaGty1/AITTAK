import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.database import init_db, close_db
from app.audit import start_audit_writer, stop_audit_writer
from app.proxy import router as proxy_router
from app.admin import router as admin_router


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


app = FastAPI(title="AI Audit Proxy", lifespan=lifespan)

app.include_router(proxy_router)
app.include_router(admin_router, prefix="/admin/api")

_template_path = Path(__file__).parent.parent / "templates" / "index.html"


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return _template_path.read_text(encoding="utf-8")
