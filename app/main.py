from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.paths import STATIC_DIR
from app.routes import admin_pages, public_api


def create_app() -> FastAPI:
    app = FastAPI(title="灵智启程 API")
    app.include_router(public_api.router, prefix="/api/public", tags=["public"])
    app.include_router(admin_pages.router, prefix="/admin", tags=["admin"])
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        return {"ok": True, "service": "lingzhi-qicheng-api"}

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    return app


app = create_app()
