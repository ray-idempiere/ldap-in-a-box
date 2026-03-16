import subprocess
import email
from email.policy import default
import json
import logging
import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class iDempiereSettings(BaseSettings):
    IDEMPIERE_URL: str = "http://idempiere:8080"
    IDEMPIERE_CLIENT_ID: str = "11"
    IDEMPIERE_ROLE_ID: str = "102"
    IDEMPIERE_ORG_ID: str = "11"
    IDEMPIERE_WAREHOUSE_ID: str = "103"
    IDEMPIERE_USER: str = "admin"
    IDEMPIERE_PASS: str = "admin"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = iDempiereSettings()

def parse_postcat_output(queue_id: str):
    """Parses `postcat -q <queue_id>` to extract the email content."""
    try:
        result = subprocess.run(['postcat', '-q', queue_id], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to postcat {queue_id}: {result.stderr}")
            return None
        
        # postcat output contains both postfix envelope info and the message itself.
        # We need to find the start of the message (usually after '*** MESSAGE CONTENTS ... ***')
        output = result.stdout
        
        # Finding the line starting with *** MESSAGE CONTENTS
        msg_start = -1
        lines = output.splitlines()
        for i, line in enumerate(lines):
            if line.startswith('*** MESSAGE CONTENTS'):
                msg_start = output.find(line) + len(line)
                break
        
        if msg_start == -1:
            logger.error(f"Could not find MESSAGE CONTENTS in postcat output for {queue_id}")
            return None
            
        # Finding the line starting with *** HEADER EXTRACTED
        msg_end = -1
        for line in lines:
            if line.startswith('*** HEADER EXTRACTED'):
                msg_end = output.find(line)
                break
            
        if msg_end == -1:
            raw_msg = output[msg_start:].strip()
        else:
            raw_msg = output[msg_start:msg_end].strip()
            
        msg = email.message_from_string(raw_msg, policy=default)

        # Extract plain text body
        plain_part = msg.get_body(preferencelist=('plain',))
        body_text = plain_part.get_content() if plain_part else ""

        # Extract HTML body
        html_part = msg.get_body(preferencelist=('html',))
        body_html = html_part.get_content() if html_part else ""

        return {
            "queue_id": queue_id,
            "sender": msg.get("From", ""),
            "subject": msg.get("Subject", ""),
            "recipient": msg.get("To", ""),
            "body_text": body_text,
            "body_html": body_html,
        }
    except Exception as e:
        logger.error(f"Error parsing postcat for {queue_id}: {e}")
        return None

def get_held_queue_ids():
    """Returns a list of Queue IDs currently hold by Postfix."""
    try:
        # postqueue -p lists the queue. 
        # Held messages have a '!' suffix in their queue ID (e.g. 1A2B3D4C!)
        result = subprocess.run(['postqueue', '-p'], capture_output=True, text=True)
        if result.returncode != 0 and result.returncode != 1:  # 1 can be returned if queue is empty
            logger.error(f"Failed to run postqueue -p (code {result.returncode}): {result.stderr}")
            return []
            
        logger.info(f"Raw postqueue output:\n{result.stdout}")
        
        queue_ids = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith('-Queue ID-') or line.startswith('--'):
                continue
            
            # Postfix output typically starts with Queue ID
            if '!' in line:
                q_id = line.split()[0].replace('!', '')
                logger.info(f"Found held Queue ID: {q_id}")
                queue_ids.append(q_id)
        return queue_ids
    except Exception as e:
        logger.error(f"Error checking postqueue: {e}")
        return []

def scan_and_forward_held_mails():
    """Scans hold queue and pushes to iDempiere"""
    logger.info("Scanning Postfix hold queue...")
    queue_ids = get_held_queue_ids()
    logger.info(f"Detected {len(queue_ids)} held messages.")
    if not queue_ids:
        return
        
    for q_id in queue_ids:
        # Check if we already processed this queue_id (can implement a local sqlite cache or file if needed)
        # For MVP, we will assume if it's in hold, we should try to push it. 
        # *IMPORTANT*: iDempiere API needs a way to NOT duplicate if we push multiple times, 
        # or we rely on iDempiere to return 4xx if MX_RBL_UU already exists.
        
        mail_info = parse_postcat_output(q_id)
        if not mail_info:
            continue
            
        logger.info(f"Intercepted mail from {mail_info['sender']} to {mail_info['recipient']} [Queue ID: {q_id}]")
        push_to_idempiere(mail_info)

def push_to_idempiere(mail_info: dict):
    # 1. Login to get token
    auth_payload = {
        "clientId": settings.IDEMPIERE_CLIENT_ID,
        "roleId": settings.IDEMPIERE_ROLE_ID,
        "organizationId": settings.IDEMPIERE_ORG_ID,
        "warehouseId": settings.IDEMPIERE_WAREHOUSE_ID,
        "userName": settings.IDEMPIERE_USER,
        "password": settings.IDEMPIERE_PASS
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            login_resp = client.post(f"{settings.IDEMPIERE_URL}/api/v1/auth/tokens", json=auth_payload)
            if login_resp.status_code not in [200, 201]:
                logger.error(f"iDempiere Login failed: {login_resp.text}")
                return
            token = login_resp.json().get("token")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 2. Get User ID by Email (Extract email address from From: Header, e.g. "User <user@test.com>" -> user@test.com)
            sender_email = mail_info["sender"]
            if "<" in sender_email and ">" in sender_email:
                sender_email = sender_email.split("<")[1].split(">")[0]
                
            user_query_resp = client.get(
                f"{settings.IDEMPIERE_URL}/api/v1/models/ad_user?filter=email eq '{sender_email}'",
                headers=headers
            )
            
            ad_user_id = None
            if user_query_resp.status_code == 200:
                users = user_query_resp.json().get("records", [])
                if users:
                    ad_user_id = users[0].get("AD_User_ID")
            
            # 3. Create MX_RBL Document
            create_payload = {
                "Sender": sender_email,
                "Description": mail_info["subject"],
                "Host": mail_info["queue_id"],
                "Processing": "Y",
            }
            if ad_user_id:
                create_payload["AD_User_ID"] = ad_user_id
                
            create_resp = client.post(
                f"{settings.IDEMPIERE_URL}/api/v1/models/mx_rbl",
                headers=headers,
                json=create_payload
            )
            
            if create_resp.status_code in [200, 201]:
                logger.info(f"Successfully created RBL in iDempiere for Queue ID: {mail_info['queue_id']}")
            else:
                logger.error(f"Failed to create RBL: {create_resp.text}")
                
    except Exception as e:
        logger.error(f"Error communicating with iDempiere: {e}")
