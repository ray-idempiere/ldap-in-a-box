from fastapi import APIRouter, HTTPException, Depends
import subprocess
import logging
from app.mail_monitor import get_held_queue_ids, parse_postcat_output
from app.auth import require_admin

router = APIRouter(prefix="/api/v1/mail", tags=["Mail Integration"])
logger = logging.getLogger(__name__)

@router.post("/release/{queue_id}")
async def release_mail(queue_id: str, _=Depends(require_admin)):
    """
    Releases a held message from the Postfix queue (Runs postsuper -H)
    """
    try:
        # Prevent any basic shell injection
        if not queue_id.isalnum() and not queue_id.replace('!', '').isalnum():
            raise HTTPException(status_code=400, detail="Invalid queue ID format")
            
        result = subprocess.run(['postsuper', '-H', queue_id], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to release mail {queue_id}: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to release check logs: {result.stderr}")
            
        # Flush queue to trigger immediate delivery attempt
        subprocess.run(['postqueue', '-f'], capture_output=True, text=True)

        logger.info(f"Successfully released queue ID {queue_id}")
        return {"status": "success", "message": f"Mail {queue_id} released"}
        
    except Exception as e:
        logger.error(f"Error releasing mail {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/drop/{queue_id}")
async def drop_mail(queue_id: str, _=Depends(require_admin)):
    """
    Drops/Deletes a message from the Postfix queue (Runs postsuper -d)
    """
    try:
         # Prevent any basic shell injection
        if not queue_id.isalnum() and not queue_id.replace('!', '').isalnum():
            raise HTTPException(status_code=400, detail="Invalid queue ID format")
            
        result = subprocess.run(['postsuper', '-d', queue_id], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to drop mail {queue_id}: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to drop check logs: {result.stderr}")
            
        logger.info(f"Successfully dropped queue ID {queue_id}")
        return {"status": "success", "message": f"Mail {queue_id} dropped"}
        
    except Exception as e:
        logger.error(f"Error dropping mail {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_mail_queue(_=Depends(require_admin)):
    """
    Returns all messages currently held in the Postfix queue with parsed headers.
    Skips any message that cannot be parsed (postcat failure).
    """
    queue_ids = get_held_queue_ids()
    messages = []
    for qid in queue_ids:
        info = parse_postcat_output(qid)
        if info is None:
            continue
        messages.append({
            "queue_id": qid,
            "sender": info.get("sender", ""),
            "recipient": info.get("recipient", ""),
            "subject": info.get("subject", ""),
        })
    return {"count": len(messages), "messages": messages}
