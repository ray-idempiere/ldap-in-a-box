from fastapi import APIRouter, HTTPException, status

from app.auth import require_admin, Depends
from app.models.group import GroupCreate, GroupUpdate, GroupResponse, MemberAction
from app.services import group_service

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse])
def list_groups(_=Depends(require_admin)):
    return group_service.list_groups()


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(data: GroupCreate, _=Depends(require_admin)):
    existing = group_service.get_group(data.cn)
    if existing:
        raise HTTPException(status_code=409, detail=f"Group {data.cn} already exists")
    return group_service.create_group(data)


@router.get("/{cn}", response_model=GroupResponse)
def get_group(cn: str, _=Depends(require_admin)):
    group = group_service.get_group(cn)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.put("/{cn}", response_model=GroupResponse)
def update_group(cn: str, data: GroupUpdate, _=Depends(require_admin)):
    group = group_service.update_group(cn, data)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("/{cn}/members", status_code=status.HTTP_204_NO_CONTENT)
def add_member(cn: str, data: MemberAction, _=Depends(require_admin)):
    if not group_service.add_member(cn, data.uid):
        raise HTTPException(status_code=404, detail="Group not found")


@router.delete("/{cn}/members", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(cn: str, data: MemberAction, _=Depends(require_admin)):
    if not group_service.remove_member(cn, data.uid):
        raise HTTPException(status_code=404, detail="Group not found")
