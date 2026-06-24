"""App entry point. Loads .env, mounts middleware + routers, serves frontend/dist."""
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(".env")

import importlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from middleware import log, middleware

PORT = int(os.getenv("PORT", 8001))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from modules.supabase import close_session, init
    await init()  # create the service-role admin client (internal ops)
    yield
    await close_session()


app = FastAPI(title="App", version="1.0.0", lifespan=lifespan)
middleware.add_middlewares(app)


# MARK: Auto-discover routers from api/
_MARKER = b"from fastapi import APIRouter"


def include_all_routers(directory: str, prefix: str):
    """Import .py files under `directory` that define an APIRouter named `router`."""
    api_dir = Path(__file__).parent / directory
    for py in sorted(api_dir.rglob("*.py")):
        if _MARKER not in py.read_bytes():
            continue
        module = api_dir.name + "." + ".".join(py.relative_to(api_dir).with_suffix("").parts)
        try:
            app.include_router(importlib.import_module(module).router, prefix=prefix)
        except Exception as e:
            log.error(f"Router error {module}: {e}")


include_all_routers("api", "/api")

app.frontend("/", directory="../../frontend/dist", check_dir=False)  # SPA fallback to index.html (React handles 404 routing)

if __name__ == "__main__":
    import uvicorn
    os.chdir(Path(__file__).parent)  # so reload can import main:app and find api/
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)  # 0.0.0.0: reach it from your LAN
