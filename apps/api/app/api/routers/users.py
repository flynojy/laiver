from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import BootstrapUserResponse, UserCreate, UserRead

router = APIRouter()


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/bootstrap", response_model=BootstrapUserResponse)
def bootstrap_user(db: Session = Depends(get_db)) -> BootstrapUserResponse:
    existing = db.scalar(select(User).order_by(User.created_at))
    if existing:
        return BootstrapUserResponse(user=existing, created=False)

    user = User(
        email="local-operator@example.com",
        display_name="Local Operator",
        preferences={"theme": "modern-console"},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return BootstrapUserResponse(user=user, created=True)

