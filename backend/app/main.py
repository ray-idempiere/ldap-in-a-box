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
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.isdir(frontend_dir) and os.path.isfile(frontend_index):
        return FileResponse(frontend_index)
        
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
