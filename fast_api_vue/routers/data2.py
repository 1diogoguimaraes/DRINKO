# routers/data.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from db.database import get_db
from db import models

router = APIRouter(prefix="/data", tags=["data"])

TABLE_MAP = {
    "matches": models.Match,
    "teams": models.Team,
    "players": models.Player,
    "results": models.Result,
}

@router.get("/{table_name}")
def get_table_data(table_name: str, db: Session = Depends(get_db)):
    model = TABLE_MAP.get(table_name)
    if not model:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    rows = db.query(model).all()
    return [
        {k: v for k, v in row.__dict__.items() if not k.startswith("_")}
        for row in rows
    ]


@router.patch("/{table_name}/{item_id}")
def update_table_item(
    table_name: str,
    item_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    model = TABLE_MAP.get(table_name)
    if not model:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    row = db.query(model).filter(model.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    for field, value in data.items():
        if hasattr(row, field):
            setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return {
        "status": "updated",
        "row": {k: v for k, v in row.__dict__.items() if not k.startswith("_")},
    }


@router.delete("/{table_name}/{item_id}")
def delete_table_item(table_name: str, item_id: int, db: Session = Depends(get_db)):
    model = TABLE_MAP.get(table_name)
    if not model:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    row = db.query(model).filter(model.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": item_id}
