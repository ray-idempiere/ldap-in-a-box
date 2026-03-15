from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LDAP-in-a-Box", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "version": "0.2.0"}

from app.routers import auth, users, groups, backup, tree, entry, schema

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(backup.router)
app.include_router(tree.router)
app.include_router(entry.router)
app.include_router(schema.router)

import os
from fastapi.staticfiles import StaticFiles

# Serve frontend static files in production
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "static")
frontend_assets = os.path.join(frontend_dir, "assets")

if os.path.isdir(frontend_assets):
    app.mount("/assets", StaticFiles(directory=frontend_assets, html=False), name="frontend-assets")

@app.get("/")
@app.get("/{full_path:path}")
async def serve_spa_fallback(full_path: str = ""):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    
    # If the user requested a specific file like favicon.svg that exists in static
    requested_file = os.path.join(frontend_dir, full_path)
    if os.path.isfile(requested_file) and not full_path == "":
        return FileResponse(requested_file)
        
    # Otherwise fallback to index.html for Vue Router SPA
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.isdir(frontend_dir) and os.path.isfile(frontend_index):
        return FileResponse(frontend_index)
        
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
