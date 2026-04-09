from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

# Strict validation choices
class SeverityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class StatusEnum(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"

# Frontend se jo data aayega (Create Ticket)
class TicketCreate(BaseModel):
    issue_type: str
    location: str
    device_id: str
    severity: SeverityEnum

# Frontend ko jo data return hoga (Full Ticket Details)
class TicketResponse(TicketCreate):
    ticket_id: int
    status: StatusEnum
    assigned_engineer: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # SQLAlchemy object ko JSON me convert karne ke liye