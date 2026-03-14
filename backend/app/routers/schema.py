from fastapi import APIRouter, Depends
from app.auth import require_admin

router = APIRouter(prefix="/api/v2/schema", tags=["schema"])

TEMPLATES = [
    {
        "id": "organizationalUnit",
        "name": "Organizational Unit (OU)",
        "objectClasses": ["top", "organizationalUnit"],
        "rdn_attribute": "ou",
        "required": ["ou"],
        "optional": ["description"]
    },
    {
        "id": "inetOrgPerson",
        "name": "User (inetOrgPerson)",
        "objectClasses": ["top", "person", "organizationalPerson", "inetOrgPerson"],
        "rdn_attribute": "uid",
        "required": ["uid", "cn", "sn"],
        "optional": ["givenName", "mail", "userPassword", "telephoneNumber", "description"]
    },
    {
        "id": "posixGroup",
        "name": "Group (posixGroup)",
        "objectClasses": ["top", "posixGroup"],
        "rdn_attribute": "cn",
        "required": ["cn", "gidNumber"],
        "optional": ["description", "memberUid"]
    },
    {
        "id": "custom",
        "name": "Custom Entry",
        "objectClasses": [],
        "rdn_attribute": "",
        "required": [],
        "optional": []
    }
]

@router.get("/templates")
def get_templates(_=Depends(require_admin)):
    return TEMPLATES
