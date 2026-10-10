import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.models import Base

class FinTwinScenario(Base):
    __tablename__ = "fintwin_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    scenario_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    input_parameters = Column(Text, nullable=False) # JSON string representation
    duration_months = Column(Integer, default=12, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    company = relationship("Company")
    simulations = relationship("FinTwinSimulation", back_populates="scenario", cascade="all, delete-orphan")


class FinTwinSimulation(Base):
    __tablename__ = "fintwin_simulations"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("fintwin_scenarios.id"), nullable=False)
    baseline_snapshot = Column(Text, nullable=False) # JSON string representation
    projected_results = Column(Text, nullable=False) # JSON string representation
    risk_assessment = Column(Text, nullable=False) # JSON string representation
    assumptions = Column(Text, nullable=False) # JSON string representation
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scenario = relationship("FinTwinScenario", back_populates="simulations")
