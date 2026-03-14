from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LDAP-in-a-Box", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

from app.routers import auth, users, groups, backup

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(backup.router)
