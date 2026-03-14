from pydantic import BaseModel


class UserCreate(BaseModel):
    uid: str
    cn: str  # full name
    sn: str  # surname
    given_name: str = ""
    mail: str = ""
    password: str
    is_vpn: str = "N"  # Y/N


class UserUpdate(BaseModel):
    cn: str | None = None
    sn: str | None = None
    given_name: str | None = None
    mail: str | None = None
    is_vpn: str | None = None


class UserResponse(BaseModel):
    uid: str
    dn: str
    cn: str
    sn: str
    given_name: str = ""
    mail: str = ""
    is_vpn: str = "N"
    enabled: bool = True
    groups: list[str] = []


class PasswordChange(BaseModel):
    new_password: str
