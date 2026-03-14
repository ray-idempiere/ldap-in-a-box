import ldap
from fastapi import APIRouter, HTTPException, Query, Depends
from app.auth import require_admin
from app.services.ldap_service import ldap_service
from app.config import settings

router = APIRouter(prefix="/api/v2/tree", tags=["tree"])

def process_entry(dn, attrs):
    decoded = {}
    for k, v_list in attrs.items():
        decoded[k] = [v.decode('utf-8') for v in v_list]
    
    rdn = dn.split(',')[0]
    oc = decoded.get("objectClass", [])
    has_children = "organizationalUnit" in oc or "organization" in oc or "dcObject" in oc
    
    return {
        "dn": dn,
        "rdn": rdn,
        "objectClass": oc,
        "hasChildren": has_children
    }

@router.get("", response_model=list[dict])
def get_tree(base_dn: str = Query(..., description="The Base DN to search under"), _=Depends(require_admin)):
    try:
        results = ldap_service.search(base_dn, "(objectClass=*)", scope=ldap.SCOPE_ONELEVEL)
        return [process_entry(dn, attrs) for dn, attrs in results if dn is not None]
    except ldap.NO_SUCH_OBJECT:
        raise HTTPException(status_code=404, detail="Base DN not found")
    except ldap.LDAPError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/root", response_model=dict)
def get_tree_root(_=Depends(require_admin)):
    base_dn = settings.ldap_base_dn
    try:
        root_res = ldap_service.search(base_dn, "(objectClass=*)", scope=ldap.SCOPE_BASE)
        if not root_res:
            raise HTTPException(status_code=404, detail="Root DN not found")
        dn, attrs = root_res[0]
        root_node = process_entry(dn, attrs)
        
        children_res = ldap_service.search(base_dn, "(objectClass=*)", scope=ldap.SCOPE_ONELEVEL)
        children = [process_entry(c_dn, c_attrs) for c_dn, c_attrs in children_res if c_dn is not None]
        
        root_node["children"] = children
        # Force hasChildren to true since it has children
        root_node["hasChildren"] = len(children) > 0
        return root_node
    except ldap.LDAPError as e:
        raise HTTPException(status_code=500, detail=str(e))
