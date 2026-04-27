from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.runtime import Skill
from app.schemas.runtime import SkillCreate, SkillInstallRequest, SkillInvocationRead, SkillRead
from app.services.skill_runtime import skill_runtime

router = APIRouter()


@router.get("", response_model=list[SkillRead])
def list_skills(db: Session = Depends(get_db)) -> list[Skill]:
    return db.scalars(select(Skill).order_by(Skill.created_at.asc())).all()


@router.get("/invocations", response_model=list[SkillInvocationRead])
def list_skill_invocations(db: Session = Depends(get_db)) -> list[SkillInvocationRead]:
    return skill_runtime.recent_invocations(db)


@router.post("", response_model=SkillRead)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)) -> Skill:
    row = Skill(
        **{
            **payload.model_dump(),
            "manifest": payload.manifest.model_dump(),
        }
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/seed", response_model=list[SkillRead])
def seed_builtin_skills(db: Session = Depends(get_db)) -> list[Skill]:
    return skill_runtime.sync_builtin_skills(db)


@router.post("/install", response_model=SkillRead)
def install_skill(payload: SkillInstallRequest, db: Session = Depends(get_db)) -> Skill:
    try:
        return skill_runtime.install_skill(db, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "cannot be overwritten" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/install/upload", response_model=SkillRead)
async def install_skill_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Skill:
    try:
        payload = skill_runtime.parse_skill_package(
            filename=file.filename or "skill-package.json",
            content=await file.read(),
        )
        return skill_runtime.install_skill(db, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "cannot be overwritten" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{skill_id}/enable", response_model=SkillRead)
def enable_skill(skill_id: str, db: Session = Depends(get_db)) -> Skill:
    row = skill_runtime.enable_skill(db, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    return row


@router.post("/{skill_id}/disable", response_model=SkillRead)
def disable_skill(skill_id: str, db: Session = Depends(get_db)) -> Skill:
    row = skill_runtime.disable_skill(db, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    return row


@router.delete("/{skill_id}")
def delete_skill(skill_id: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    deleted = skill_runtime.uninstall_skill(db, skill_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"deleted": True}
