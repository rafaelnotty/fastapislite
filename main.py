from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

# Configuración de la conexión a SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./sensordata.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de la base de datos (Tabla 'sensor_data')
class SensorDataDB(Base):
    __tablename__ = 'sensor_data'

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, unique=True, index=True)
    temperature = Column(Float)
    humidity = Column(Float)

# Crear la tabla en la base de datos
Base.metadata.create_all(bind=engine)

# Modelo Pydantic para la validación de datos de entrada
class SensorData(BaseModel):
    sensor_id: str
    temperature: float
    humidity: float

    class Config:
        orm_mode = True

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/sensor-data/")
async def create_sensor_data(data: SensorData, db: Session = Depends(get_db)):
    # Verificar si ya existe un registro con el mismo sensor_id
    existing_data = db.query(SensorDataDB).filter(SensorDataDB.sensor_id == data.sensor_id).first()
    if existing_data:
        raise HTTPException(status_code=400, detail="Sensor data already exists")

    # Crear una nueva entrada de datos del sensor
    new_sensor_data = SensorDataDB(sensor_id=data.sensor_id, temperature=data.temperature, humidity=data.humidity)
    db.add(new_sensor_data)
    db.commit()
    db.refresh(new_sensor_data)
    
    return {"status": "success", "id": new_sensor_data.id}

@app.get("/sensor-data/", response_model=List[SensorData])
async def get_all_sensor_data(db: Session = Depends(get_db)):
    sensor_data = db.query(SensorDataDB).all()
    return sensor_data

@app.get("/sensor-data/{sensor_id}", response_model=SensorData)
async def get_sensor_data(sensor_id: str, db: Session = Depends(get_db)):
    sensor_data = db.query(SensorDataDB).filter(SensorDataDB.sensor_id == sensor_id).first()
    if sensor_data:
        return sensor_data
    raise HTTPException(status_code=404, detail="Sensor data not found")

@app.delete("/sensor-data/{sensor_id}")
async def delete_sensor_data(sensor_id: str, db: Session = Depends(get_db)):
    sensor_data = db.query(SensorDataDB).filter(SensorDataDB.sensor_id == sensor_id).first()
    if sensor_data:
        db.delete(sensor_data)
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Sensor data not found")

@app.get("/")
async def read_root():
    return {"message": "FastAPI + SQLite IoT Data Service"}
