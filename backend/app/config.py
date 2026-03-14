from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ldap_host: str = "ldap-master"
    ldap_port: int = 389
    ldap_domain: str = "example.com"
    ldap_admin_password: str = "change_me"
    jwt_secret: str = "change_me_to_random_string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    @property
    def ldap_base_dn(self) -> str:
        return ",".join(f"dc={part}" for part in self.ldap_domain.split("."))

    @property
    def ldap_admin_dn(self) -> str:
        return f"cn=admin,{self.ldap_base_dn}"

    @property
    def ldap_uri(self) -> str:
        return f"ldap://{self.ldap_host}:{self.ldap_port}"

    class Config:
        env_prefix = ""


settings = Settings()
