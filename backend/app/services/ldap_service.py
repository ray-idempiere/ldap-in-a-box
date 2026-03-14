import ldap
from app.config import settings


class LDAPService:
    """Low-level wrapper around python-ldap operations."""

    def _connect(self, bind_dn: str | None = None, password: str | None = None) -> ldap.ldapobject.LDAPObject:
        conn = ldap.initialize(settings.ldap_uri)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        dn = bind_dn or settings.ldap_admin_dn
        pw = password or settings.ldap_admin_password
        conn.simple_bind_s(dn, pw)
        return conn

    def authenticate(self, dn: str, password: str) -> bool:
        try:
            conn = self._connect(dn, password)
            conn.unbind_s()
            return True
        except ldap.INVALID_CREDENTIALS:
            return False

    def search(self, base_dn: str, filter_str: str, attrs: list[str] | None = None, scope: int = ldap.SCOPE_SUBTREE) -> list[tuple]:
        conn = self._connect()
        try:
            results = conn.search_s(base_dn, scope, filter_str, attrs)
            return [(dn, entry) for dn, entry in results if dn is not None]
        finally:
            conn.unbind_s()

    def add(self, dn: str, attrs: list[tuple]) -> None:
        conn = self._connect()
        try:
            conn.add_s(dn, attrs)
        finally:
            conn.unbind_s()

    def modify(self, dn: str, mod_list: list[tuple]) -> None:
        conn = self._connect()
        try:
            conn.modify_s(dn, mod_list)
        finally:
            conn.unbind_s()

    def delete(self, dn: str) -> None:
        conn = self._connect()
        try:
            conn.delete_s(dn)
        finally:
            conn.unbind_s()


ldap_service = LDAPService()
