from pydantic import BaseModel


class GroupCreate(BaseModel):
    cn: str
    description: str = ""


class GroupUpdate(BaseModel):
    description: str | None = None


class GroupResponse(BaseModel):
    cn: str
    dn: str
    description: str = ""
    members: list[str] = []


class MemberAction(BaseModel):
    uid: str
