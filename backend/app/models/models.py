from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="farmer")  # farmer / admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farms = relationship("Farm", back_populates="owner", cascade="all, delete")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="farms")
    fields = relationship("Field", back_populates="farm", cascade="all, delete")


class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False)
    name = Column(String, nullable=False)
    crop_type = Column(String, nullable=False)  # wheat, rice, cotton, sugarcane...
    soil_type = Column(String, default="loamy")  # sandy, loamy, clay
    area_acres = Column(Float, default=1.0)
    planting_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="fields")
    readings = relationship("SensorReading", back_populates="field", cascade="all, delete")
    forecasts = relationship("Forecast", back_populates="field", cascade="all, delete")
    alerts = relationship("Alert", back_populates="field", cascade="all, delete")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    soil_moisture = Column(Float, nullable=False)   # percent 0-100
    temperature = Column(Float, nullable=False)     # deg C
    humidity = Column(Float, nullable=False)        # percent
    rainfall = Column(Float, default=0.0)           # mm
    wind_speed = Column(Float, default=0.0)         # km/h

    field = relationship("Field", back_populates="readings")


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    target_date = Column(Date, nullable=False)
    predicted_water_mm = Column(Float, nullable=False)
    model_name = Column(String, default="xgboost")

    field = relationship("Field", back_populates="forecasts")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    severity = Column(String, default="info")  # info / warning / critical
    alert_type = Column(String, default="general")  # dry_soil / heat_stress / heavy_rain / sensor_offline
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)

    field = relationship("Field", back_populates="alerts")