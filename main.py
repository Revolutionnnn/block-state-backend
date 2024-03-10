from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Property(Base):
    __tablename__ = 'properties'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    image = Column(String)
    location = Column(String)
    price = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    area = Column(Integer)
    rooms = Column(Integer)
    bathrooms = Column(Integer)
    garage = Column(Boolean, default=False)
    is_sold = Column(Boolean, default=False)

    class Config:
        orm_mode = True

class PropertyChangeLog(Base):
    __tablename__ = 'property_change_logs'
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'))
    changed_field = Column(String)
    old_value = Column(String)
    new_value = Column(String)
    changed_at = Column(DateTime, default=datetime.utcnow)

    property = relationship("Property", back_populates="changes")

Property.changes = relationship("PropertyChangeLog", order_by=PropertyChangeLog.id, back_populates="property")


class RealEstateModel(BaseModel):
    name: str
    description: str
    image: str
    location: str
    price: str
    address: str
    area: int
    rooms: int
    bathrooms: int
    garage: bool
    is_sold: bool = False

class PropertyChangeLogModel(BaseModel):
    id: int
    property_id: int
    changed_field: str
    old_value: str
    new_value: str
    changed_at: datetime

    class Config:
        orm_mode = True

engine = create_engine("sqlite:///real_estate.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/properties")
async def create_property(property: RealEstateModel, db: Session = Depends(get_db)):
    db_property = Property(**property.dict())
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return {"message": "Propiedad creada exitosamente", "property_id": db_property.id}

@app.get("/properties", response_model=List[RealEstateModel])
async def read_properties(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    properties = db.query(Property).offset(skip).limit(limit).all()
    return properties

@app.get("/properties/{property_id}", response_model=RealEstateModel)
async def read_property(property_id: int, db: Session = Depends(get_db)):
    db_property = db.query(Property).filter(Property.id == property_id).first()
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return db_property

@app.put("/properties/{property_id}", response_model=RealEstateModel)
async def update_property(property_id: int, updated_property: RealEstateModel, db: Session = Depends(get_db)):
    db_property = db.query(Property).filter(Property.id == property_id).first()
    if db_property is None:
        raise HTTPException(status_code=404, detail="Property not found")
    
    update_data = updated_property.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(db_property, field) and value != getattr(db_property, field):
            log = PropertyChangeLog(property_id=db_property.id, changed_field=field, old_value=str(getattr(db_property, field)), new_value=str(value), changed_at=datetime.utcnow())
            db.add(log)
            setattr(db_property, field, value)
    
    db.commit()
    db.refresh(db_property)
    return db_property

@app.get("/properties/{property_id}/changes", response_model=List[PropertyChangeLogModel])
async def read_property_changes(property_id: int, db: Session = Depends(get_db)):
    property_changes = db.query(PropertyChangeLog).filter(PropertyChangeLog.property_id == property_id).all()
    if property_changes is None or len(property_changes) == 0:
        raise HTTPException(status_code=404, detail="No changes found for the specified property")
    return property_changes