from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import Farm, User
from app.models.models import Field as FieldModel
from app.schemas.farm import FarmCreate, FarmOut, FieldCreate, FieldOut

router = APIRouter(prefix="/api", tags=["Farms & Fields"])


# ---------- helpers (ownership checks) ----------
def get_farm_or_404(db: Session, farm_id: int, user: User) -> Farm:
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if farm is None or (user.role != "admin" and farm.owner_id != user.id):
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


def get_field_or_404(db: Session, field_id: int, user: User) -> FieldModel:
    field = db.query(FieldModel).filter(FieldModel.id == field_id).first()
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    try:
        get_farm_or_404(db, field.farm_id, user)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


# ---------- farms ----------
@router.post("/farms", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(
    data: FarmCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = data.name.strip()
    exists = (
        db.query(Farm).filter(Farm.owner_id == user.id, Farm.name == name).first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="You already have a farm with this name")

    farm = Farm(
        name=name,
        location=data.location.strip(),
        latitude=data.latitude,
        longitude=data.longitude,
        owner_id=user.id,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/farms", response_model=list[FarmOut])
def list_farms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Farm)
    if user.role != "admin":
        query = query.filter(Farm.owner_id == user.id)
    return query.order_by(Farm.id).all()


@router.get("/farms/{farm_id}", response_model=FarmOut)
def get_farm(
    farm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return get_farm_or_404(db, farm_id, user)


@router.delete("/farms/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    farm = get_farm_or_404(db, farm_id, user)
    db.delete(farm)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- fields ----------
@router.post(
    "/farms/{farm_id}/fields",
    response_model=FieldOut,
    status_code=status.HTTP_201_CREATED,
)
def create_field(
    farm_id: int,
    data: FieldCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    farm = get_farm_or_404(db, farm_id, user)
    name = data.name.strip()

    exists = (
        db.query(FieldModel)
        .filter(FieldModel.farm_id == farm.id, FieldModel.name == name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="This farm already has a field with this name")

    field = FieldModel(
        farm_id=farm.id,
        name=name,
        crop_type=data.crop_type,
        soil_type=data.soil_type,
        area_acres=data.area_acres,
        planting_date=data.planting_date,
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/farms/{farm_id}/fields", response_model=list[FieldOut])
def list_fields(
    farm_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    farm = get_farm_or_404(db, farm_id, user)
    return (
        db.query(FieldModel)
        .filter(FieldModel.farm_id == farm.id)
        .order_by(FieldModel.id)
        .all()
    )


@router.get("/fields/{field_id}", response_model=FieldOut)
def get_field(
    field_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return get_field_or_404(db, field_id, user)


@router.delete("/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(
    field_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    field = get_field_or_404(db, field_id, user)
    db.delete(field)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)