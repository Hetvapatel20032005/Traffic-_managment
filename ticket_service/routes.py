from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from . import models, schemas
from .database import get_db

router = APIRouter()

# 1. CREATE TICKET (100% Local, No Third-Party API)
@router.post("/tickets/", response_model=schemas.TicketResponse)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    db_ticket = models.Ticket(**ticket.model_dump())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

# 2. GET ALL TICKETS
@router.get("/tickets/", response_model=List[schemas.TicketResponse])
def get_all_tickets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Ticket).offset(skip).limit(limit).all()

# 3. GET TICKET BY ID
@router.get("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

# 4. ASSIGN ENGINEER
@router.put("/tickets/{ticket_id}/assign")
def assign_engineer(ticket_id: int, engineer_name: str, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.assigned_engineer = engineer_name
    ticket.status = "in_progress"
    db.commit()
    return {"message": f"Ticket assigned to {engineer_name}", "status": ticket.status}

# 5. CLOSE TICKET
@router.put("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = "resolved"
    ticket.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Ticket closed successfully", "resolved_at": ticket.resolved_at}

