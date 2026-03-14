import subprocess

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.auth import require_admin
from app.config import settings

router = APIRouter(prefix="/api/v1/backup", tags=["backup"])


@router.post("", response_class=PlainTextResponse)
def trigger_backup(_=Depends(require_admin)):
    """Export all LDAP data as LDIF."""
    result = subprocess.run(
        [
            "ldapsearch", "-x",
            "-H", settings.ldap_uri,
            "-D", settings.ldap_admin_dn,
            "-w", settings.ldap_admin_password,
            "-b", settings.ldap_base_dn,
            "-LLL",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return PlainTextResponse(f"Backup failed: {result.stderr}", status_code=500)
    return PlainTextResponse(
        result.stdout,
        headers={"Content-Disposition": "attachment; filename=ldap-backup.ldif"},
    )
