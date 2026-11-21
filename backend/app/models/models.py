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
    preferred_language = Column(
        String, nullable=False, default="en", server_default="en"
    )  # en / hi / mr
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
    irrigation_logs = relationship(
        "IrrigationLog", back_populates="field", cascade="all, delete"
    )


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
    alert_type = Column(String, default="general")  # dry_soil / heat_stress / heavy_rain / sensor_offline
    severity = Column(String, default="info")  # info / warning / critical
    message = Column(Text, nullable=False)  # English text, kept as a fallback
    params = Column(Text, nullable=True)  # JSON with the numbers, used to translate the alert
    is_read = Column(Boolean, default=False)

    field = relationship("Field", back_populates="alerts")


class IrrigationLog(Base):
    __tablename__ = "irrigation_logs"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    minutes = Column(Float, nullable=False)
    source = Column(String, default="chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    field = relationship("Field", back_populates="irrigation_logs")


# ------------------------------------------------------------------ Government Schemes
class GovernmentScheme(Base):
    __tablename__ = "government_schemes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    benefits = Column(Text, nullable=False)
    eligibility = Column(Text, nullable=False)
    documents_required = Column(Text, nullable=False)
    application_process = Column(Text, nullable=False)
    application_url = Column(String, nullable=True)
    source_url = Column(String, nullable=False)
    last_verified = Column(Date, nullable=False)
    deadline = Column(Date, nullable=True)
    level = Column(String, nullable=False)  # central / maharashtra
    category = Column(String, nullable=True)  # income_support / insurance / credit / irrigation / mechanization / organic / market / pension
    applicable_crops = Column(Text, nullable=True)  # comma-separated or None for all
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SchemeNotification(Base):
    __tablename__ = "scheme_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String, nullable=False)  # new_scheme / deadline_approaching / scheme_updated
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    scheme = relationship("GovernmentScheme")