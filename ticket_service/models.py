from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class Ticket(Base):
    __tablename__ = "tickets"

    # Primary Key
    ticket_id = Column(Integer, primary_key=True, index=True)
    
    # Core Information
    issue_type = Column(String, index=True)      # e.g., "Camera Offline", "Sensor Failure"
    location = Column(String)                    # e.g., "Node-01 North"
    device_id = Column(String, index=True)       # e.g., "CAM-104"
    
    # Status & Priority
    severity = Column(String)                    # Low, Medium, High, Critical
    status = Column(String, default="open")      # open, in_progress, resolved
    
    # Resolution Tracking
    assigned_engineer = Column(String, nullable=True)  # Shuru mein koi assign nahi hoga
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)      # Solve hone par time aayega