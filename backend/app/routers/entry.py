import ldap
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from app.auth import require_admin
from app.services.ldap_service import ldap_service

router = APIRouter(prefix="/api/v2/entry", tags=["entry"])

def decode_attrs(attrs):
    decoded = {}
    for k, v_list in attrs.items():
        decoded[k] = [v.decode('utf-8') for v in v_list]
    return decoded

@router.get("")
def get_entry(dn: str = Query(...), _=Depends(require_admin)):
    try:
        results = ldap_service.search(dn, "(objectClass=*)", scope=ldap.SCOPE_BASE)
        if not results:
            raise HTTPException(status_code=404, detail="Entry not found")
        dn, attrs = results[0]
        return {
            "dn": dn,
            "attributes": decode_attrs(attrs)
        }
    except ldap.NO_SUCH_OBJECT:
        raise HTTPException(status_code=404, detail="Entry not found")

@router.post("", status_code=201)
def create_entry(data: dict = Body(...), _=Depends(require_admin)):
    parent_dn = data.get("parent_dn")
    rdn = data.get("rdn")
    object_classes = data.get("objectClasses", [])
    attributes = data.get("attributes", {})

    dn = f"{rdn},{parent_dn}"
    
    mod_list = []
    mod_list.append(("objectClass", [oc.encode('utf-8') for oc in object_classes]))
    for k, v in attributes.items():
        if isinstance(v, list):
            mod_list.append((k, [str(val).encode('utf-8') for val in v if val]))
        else:
            mod_list.append((k, [str(v).encode('utf-8')]))

    try:
        ldap_service.add(dn, mod_list)
        return {"dn": dn, "status": "created"}
    except ldap.ALREADY_EXISTS:
        raise HTTPException(status_code=409, detail="Entry already exists")
    except ldap.LDAPError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("")
def update_entry(dn: str = Query(...), data: dict = Body(...), _=Depends(require_admin)):
    # data is a dict of attribute replacing e.g. {"mail": ["test@example.com"], "sn": ["User"]}
    mod_list = []
    for k, vlist in data.items():
        if vlist is None or len(vlist) == 0:
            mod_list.append((ldap.MOD_DELETE, k, None))
        else:
            mod_list.append((ldap.MOD_REPLACE, k, [str(v).encode('utf-8') for v in vlist]))
    try:
        ldap_service.modify(dn, mod_list)
        return {"dn": dn, "status": "updated"}
    except ldap.NO_SUCH_OBJECT:
        raise HTTPException(status_code=404, detail="Entry not found")
    except ldap.LDAPError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("", status_code=204)
def delete_entry(dn: str = Query(...), recursive: bool = Query(False), _=Depends(require_admin)):
    try:
        if recursive:
            ldap_service.delete_tree(dn)
        else:
            ldap_service.delete(dn)
    except ldap.NOT_ALLOWED_ON_NONLEAF:
        raise HTTPException(status_code=400, detail="Cannot delete non-leaf entry without recursive=true")
    except ldap.NO_SUCH_OBJECT:
        raise HTTPException(status_code=404, detail="Entry not found")
    except ldap.LDAPError as e:
        raise HTTPException(status_code=400, detail=str(e))
