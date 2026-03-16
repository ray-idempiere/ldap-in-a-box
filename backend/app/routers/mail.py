from fastapi import APIRouter, HTTPException, Depends
import subprocess
import logging

router = APIRouter(prefix="/api/v1/mail", tags=["Mail Integration"])
logger = logging.getLogger(__name__)

@router.post("/release/{queue_id}")
async def release_mail(queue_id: str):
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
async def drop_mail(queue_id: str):
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
