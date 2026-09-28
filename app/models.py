from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.db import Base

class Experiment(Base):
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=func.now())


class Variant(Base):

    __tablename__ = "variants"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    name = Column(String(100), nullable=False)
    weight = Column(Float, default=0.5)
    is_control = Column(Boolean, default=False)


class Assignment(Base):

    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    variant_id = Column(Integer, ForeignKey("variants.id"))
    user_id = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, default=func.now())
    __table_args__ = (
        UniqueConstraint("experiment_id", "user_id", name="uq_experiment_user"),
    )

class Event(Base):

    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    variant_id = Column(Integer, ForeignKey("variants.id"))
    user_id = Column(String(100))
    event_type = Column(String(50))
    created_at = Column(DateTime, default=func.now())