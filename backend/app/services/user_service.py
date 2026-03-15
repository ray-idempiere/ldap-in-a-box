import ldap
from app.config import settings
from app.services.ldap_service import ldap_service
from app.models.user import UserCreate, UserUpdate, UserResponse


def _decode(val: list[bytes] | bytes) -> str:
    if isinstance(val, list):
        return val[0].decode("utf-8") if val else ""
    return val.decode("utf-8") if val else ""


def _user_from_entry(dn: str, entry: dict) -> UserResponse:
    return UserResponse(
        uid=_decode(entry.get("uid", [b""])),
        dn=dn,
        cn=_decode(entry.get("cn", [b""])),
        sn=_decode(entry.get("sn", [b""])),
        given_name=_decode(entry.get("givenName", [b""])),
        mail=_decode(entry.get("mail", [b""])),
        is_vpn=_decode(entry.get("isVPN", [b"N"])),
        is_mail_monitor=_decode(entry.get("IsMailMonitor", [b"N"])),
        enabled="nologin" not in _decode(entry.get("loginShell", [b""])),
    )


def list_users(search: str = "") -> list[UserResponse]:
    base = f"ou=users,{settings.ldap_base_dn}"
    if search:
        filter_str = f"(&(objectClass=inetOrgPerson)(|(uid=*{search}*)(cn=*{search}*)(mail=*{search}*)))"
    else:
        filter_str = "(objectClass=inetOrgPerson)"
    results = ldap_service.search(base, filter_str)
    return [_user_from_entry(dn, entry) for dn, entry in results]


def get_user(uid: str) -> UserResponse | None:
    base = f"ou=users,{settings.ldap_base_dn}"
    results = ldap_service.search(base, f"(uid={uid})")
    if not results:
        return None
    dn, entry = results[0]
    user = _user_from_entry(dn, entry)
    # Fetch group memberships
    group_base = f"ou=groups,{settings.ldap_base_dn}"
    groups = ldap_service.search(group_base, f"(memberUid={uid})", ["cn"])
    user.groups = [_decode(e.get("cn", [b""])) for _, e in groups]
    return user


def create_user(data: UserCreate) -> UserResponse:
    dn = f"uid={data.uid},ou=users,{settings.ldap_base_dn}"
    object_classes = [b"inetOrgPerson", b"posixAccount", b"shadowAccount", b"myorgUser"]
    attrs = [
        ("objectClass", object_classes),
        ("uid", [data.uid.encode()]),
        ("cn", [data.cn.encode()]),
        ("sn", [data.sn.encode()]),
        ("uidNumber", [b"0"]),  # will be auto-assigned in production
        ("gidNumber", [b"0"]),
        ("homeDirectory", [f"/home/{data.uid}".encode()]),
        ("loginShell", [b"/bin/bash"]),
        ("userPassword", [data.password.encode()]),
        ("isVPN", [data.is_vpn.encode()]),
        ("IsMailMonitor", [data.is_mail_monitor.encode()]),
    ]
    if data.given_name:
        attrs.append(("givenName", [data.given_name.encode()]))
    if data.mail:
        attrs.append(("mail", [data.mail.encode()]))

    ldap_service.add(dn, attrs)
    return get_user(data.uid)


def update_user(uid: str, data: UserUpdate) -> UserResponse | None:
    dn = f"uid={uid},ou=users,{settings.ldap_base_dn}"
    mod_list = []
    if data.cn is not None:
        mod_list.append((ldap.MOD_REPLACE, "cn", [data.cn.encode()]))
    if data.sn is not None:
        mod_list.append((ldap.MOD_REPLACE, "sn", [data.sn.encode()]))
    if data.given_name is not None:
        mod_list.append((ldap.MOD_REPLACE, "givenName", [data.given_name.encode()]))
    if data.mail is not None:
        mod_list.append((ldap.MOD_REPLACE, "mail", [data.mail.encode()]))
    if data.is_vpn is not None:
        mod_list.append((ldap.MOD_REPLACE, "isVPN", [data.is_vpn.encode()]))
    if data.is_mail_monitor is not None:
        mod_list.append((ldap.MOD_REPLACE, "IsMailMonitor", [data.is_mail_monitor.encode()]))
    if mod_list:
        ldap_service.modify(dn, mod_list)
    return get_user(uid)


def delete_user(uid: str) -> bool:
    dn = f"uid={uid},ou=users,{settings.ldap_base_dn}"
    try:
        ldap_service.delete(dn)
        return True
    except ldap.NO_SUCH_OBJECT:
        return False


def reset_password(uid: str, new_password: str) -> bool:
    dn = f"uid={uid},ou=users,{settings.ldap_base_dn}"
    try:
        ldap_service.modify(dn, [(ldap.MOD_REPLACE, "userPassword", [new_password.encode()])])
        return True
    except ldap.NO_SUCH_OBJECT:
        return False


def disable_user(uid: str) -> bool:
    dn = f"uid={uid},ou=users,{settings.ldap_base_dn}"
    try:
        ldap_service.modify(dn, [(ldap.MOD_REPLACE, "loginShell", [b"/usr/sbin/nologin"])])
        return True
    except ldap.NO_SUCH_OBJECT:
        return False
