import ldap
from app.config import settings
from app.services.ldap_service import ldap_service
from app.models.group import GroupCreate, GroupUpdate, GroupResponse


def _decode(val: list[bytes] | bytes) -> str:
    if isinstance(val, list):
        return val[0].decode("utf-8") if val else ""
    return val.decode("utf-8") if val else ""


def _decode_list(val: list[bytes]) -> list[str]:
    return [v.decode("utf-8") for v in val] if val else []


def _group_from_entry(dn: str, entry: dict) -> GroupResponse:
    return GroupResponse(
        cn=_decode(entry.get("cn", [b""])),
        dn=dn,
        description=_decode(entry.get("description", [b""])),
        members=_decode_list(entry.get("memberUid", [])),
    )


def list_groups() -> list[GroupResponse]:
    base = f"ou=groups,{settings.ldap_base_dn}"
    results = ldap_service.search(base, "(objectClass=posixGroup)")
    return [_group_from_entry(dn, entry) for dn, entry in results]


def get_group(cn: str) -> GroupResponse | None:
    base = f"ou=groups,{settings.ldap_base_dn}"
    results = ldap_service.search(base, f"(cn={cn})")
    if not results:
        return None
    return _group_from_entry(*results[0])


def create_group(data: GroupCreate) -> GroupResponse:
    dn = f"cn={data.cn},ou=groups,{settings.ldap_base_dn}"
    attrs = [
        ("objectClass", [b"posixGroup"]),
        ("cn", [data.cn.encode()]),
        ("gidNumber", [b"0"]),
    ]
    if data.description:
        attrs.append(("description", [data.description.encode()]))
    ldap_service.add(dn, attrs)
    return get_group(data.cn)


def update_group(cn: str, data: GroupUpdate) -> GroupResponse | None:
    dn = f"cn={cn},ou=groups,{settings.ldap_base_dn}"
    mod_list = []
    if data.description is not None:
        mod_list.append((ldap.MOD_REPLACE, "description", [data.description.encode()]))
    if mod_list:
        ldap_service.modify(dn, mod_list)
    return get_group(cn)


def add_member(cn: str, uid: str) -> bool:
    dn = f"cn={cn},ou=groups,{settings.ldap_base_dn}"
    try:
        ldap_service.modify(dn, [(ldap.MOD_ADD, "memberUid", [uid.encode()])])
        return True
    except ldap.TYPE_OR_VALUE_EXISTS:
        return True  # already a member
    except ldap.NO_SUCH_OBJECT:
        return False


def remove_member(cn: str, uid: str) -> bool:
    dn = f"cn={cn},ou=groups,{settings.ldap_base_dn}"
    try:
        ldap_service.modify(dn, [(ldap.MOD_DELETE, "memberUid", [uid.encode()])])
        return True
    except ldap.NO_SUCH_ATTRIBUTE:
        return True  # wasn't a member
    except ldap.NO_SUCH_OBJECT:
        return False
