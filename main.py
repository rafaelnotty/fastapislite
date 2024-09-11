from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

app = FastAPI()

# Database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./sensordata.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model
class SensorDataDB(Base):
    __tablename__ = 'sensor_data'

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    presion = Column(Float)
    vbatt = Column(Float)
    ibatt = Column(Float)
    pwbatt = Column(Float)
    vpv = Column(Float)
    ipv = Column(Float)
    pwpv = Column(Float)
    temp_batt = Column(Float)
    lum = Column(Float)
    power_signal = Column(Float)

Base.metadata.create_all(bind=engine)

# Pydantic model for input validation and output serialization
class SensorData(BaseModel):
    sensor_id: str
    timestamp: datetime = Field(..., example="2024-09-11 12:00:00")
    presion: float
    vbatt: float
    ibatt: float
    pwbatt: float
    vpv: float
    ipv: float
    pwpv: float
    temp_batt: float
    lum: float
    power_signal: float

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("Timestamp must be in the format YYYY-MM-DD HH:MM:SS")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/sensor-data/", response_model=dict)
async def create_sensor_data(data: SensorData, db: Session = Depends(get_db)):
    new_sensor_data = SensorDataDB(**data.model_dump())
    db.add(new_sensor_data)
    db.commit()
    db.refresh(new_sensor_data)
    return {"status": "success", "id": new_sensor_data.id}

@app.get("/sensor-data/", response_model=List[SensorData])
async def get_all_sensor_data(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    sensor_data = db.query(SensorDataDB).offset(skip).limit(limit).all()
    return [SensorData.model_validate(data) for data in sensor_data]

@app.get("/sensor-data/{sensor_id}", response_model=List[SensorData])
async def get_sensor_data(
    sensor_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date (YYYY-MM-DD HH:MM:SS)"),
    end_date: Optional[datetime] = Query(None, description="End date (YYYY-MM-DD HH:MM:SS)"),
    db: Session = Depends(get_db)
):
    query = db.query(SensorDataDB).filter(SensorDataDB.sensor_id == sensor_id)
    
    if start_date:
        query = query.filter(SensorDataDB.timestamp >= start_date)
    if end_date:
        query = query.filter(SensorDataDB.timestamp <= end_date)
    
    sensor_data = query.all()
    if not sensor_data:
        raise HTTPException(status_code=404, detail="Sensor data not found")
    return [SensorData.model_validate(data) for data in sensor_data]

@app.delete("/sensor-data/{sensor_id}")
async def delete_sensor_data(
    sensor_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date (YYYY-MM-DD HH:MM:SS)"),
    end_date: Optional[datetime] = Query(None, description="End date (YYYY-MM-DD HH:MM:SS)"),
    db: Session = Depends(get_db)
):
    # Inicializar la consulta para filtrar por sensor_id
    query = db.query(SensorDataDB).filter(SensorDataDB.sensor_id == sensor_id)
    
    # Aplicar filtro de fecha de inicio, si está presente
    if start_date:
        query = query.filter(SensorDataDB.timestamp >= start_date)
    
    # Aplicar filtro de fecha de fin, si está presente
    if end_date:
        query = query.filter(SensorDataDB.timestamp <= end_date)
    
    # Eliminar los registros coincidentes
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    
    # Retornar respuesta en función de los registros eliminados
    if deleted_count:
        return {"status": "success", "deleted_count": deleted_count}
    
    # Si no se encontró ningún registro, lanzar error 404
    raise HTTPException(status_code=404, detail="No sensor data found for the given criteria")


@app.get("/")
async def read_root():
    return {"message": "FastAPI + SQLite IoT Data Service"}

# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred.", "detail": str(exc)},
    )
