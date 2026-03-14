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


from fastapi import UploadFile, File, HTTPException
import tempfile
import os

@router.post("/restore")
async def restore_backup(file: UploadFile = File(...), _=Depends(require_admin)):
    """Import LDAP data from an uploaded LDIF file."""
    if not file.filename.endswith(".ldif"):
        raise HTTPException(status_code=400, detail="Only .ldif files are allowed")

    content = await file.read()
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ldif") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Use ldapmodify (or ldapadd) to apply the LDIF
        # -c specifies continuous operation mode (errors are reported, but execution continues)
        result = subprocess.run(
            [
                "ldapmodify", "-x", "-c",
                "-H", settings.ldap_uri,
                "-D", settings.ldap_admin_dn,
                "-w", settings.ldap_admin_password,
                "-f", tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0 and result.returncode != 68: # 68 is Entry Already Exists, which we can ignore in restore
            raise HTTPException(status_code=500, detail=f"Restore failed: {result.stderr or result.stdout}")
        
        return {"success": True, "details": "Restore completed successfully"}
    finally:
        os.unlink(tmp_path)
