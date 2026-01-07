"""
Salu Imóveis - Painel Administrativo
"""
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import os
import enum
from datetime import datetime

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Enums (mesmos do portal principal)
class ProposalType(enum.Enum):
    BUY = "BUY"
    RENT = "RENT"
    SELL = "SELL"


class ProposalStatus(enum.Enum):
    PENDING = "PENDING"
    ADMIN_APPROVED = "ADMIN_APPROVED"
    ADMIN_REJECTED = "ADMIN_REJECTED"
    BROKER_ASSIGNED = "BROKER_ASSIGNED"
    IN_CONTACT = "IN_CONTACT"
    NEGOTIATING = "NEGOTIATING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# Models (espelho do portal principal)
class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String, primary_key=True)
    type = Column(SQLEnum(ProposalType), nullable=False)
    status = Column(SQLEnum(ProposalStatus), default=ProposalStatus.PENDING)
    property_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    cpf = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    monthly_income = Column(Float, nullable=True)
    proposed_value = Column(Float, nullable=True)
    rental_period = Column(String, nullable=True)
    move_in_date = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    has_financing_approval = Column(Boolean, default=False)
    message = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    admin_approved_by = Column(String, nullable=True)
    admin_approved_at = Column(DateTime, nullable=True)
    broker_id = Column(String, nullable=True)
    broker_notes = Column(Text, nullable=True)
    broker_assigned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Broker(Base):
    __tablename__ = "brokers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)


class Property(Base):
    __tablename__ = "properties"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    city = Column(String, nullable=True)
    neighborhood = Column(String, nullable=True)
    sale_price = Column(Float, nullable=True)
    rental_price = Column(Float, nullable=True)


# App
app = FastAPI(title="Salu Admin Panel")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal"""
    # Stats
    pending_proposals = db.query(Proposal).filter(Proposal.status == ProposalStatus.PENDING).count()
    approved_proposals = db.query(Proposal).filter(Proposal.status == ProposalStatus.ADMIN_APPROVED).count()
    total_brokers = db.query(Broker).filter(Broker.is_active == True).count()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "pending_proposals": pending_proposals,
            "approved_proposals": approved_proposals,
            "total_brokers": total_brokers
        }
    })


@app.get("/propostas", response_class=HTMLResponse)
async def proposals_list(request: Request, status: str = None, db: Session = Depends(get_db)):
    """Lista de propostas"""
    query = db.query(Proposal)

    if status:
        status_map = {
            "pending": ProposalStatus.PENDING,
            "approved": ProposalStatus.ADMIN_APPROVED,
            "rejected": ProposalStatus.ADMIN_REJECTED,
            "assigned": ProposalStatus.BROKER_ASSIGNED
        }
        if status in status_map:
            query = query.filter(Proposal.status == status_map[status])

    proposals = query.order_by(Proposal.created_at.desc()).all()

    # Get properties for each proposal
    proposal_data = []
    for p in proposals:
        prop = None
        if p.property_id:
            prop = db.query(Property).filter(Property.id == p.property_id).first()
        proposal_data.append({
            "proposal": p,
            "property": prop
        })

    return templates.TemplateResponse("propostas.html", {
        "request": request,
        "proposals": proposal_data,
        "current_status": status
    })


@app.get("/proposta/{proposal_id}", response_class=HTMLResponse)
async def proposal_detail(request: Request, proposal_id: str, db: Session = Depends(get_db)):
    """Detalhes da proposta"""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    property = None
    if proposal.property_id:
        property = db.query(Property).filter(Property.id == proposal.property_id).first()

    brokers = db.query(Broker).filter(Broker.is_active == True).all()

    return templates.TemplateResponse("proposta_detalhe.html", {
        "request": request,
        "proposal": proposal,
        "property": property,
        "brokers": brokers
    })


@app.post("/proposta/{proposal_id}/aprovar")
async def approve_proposal(
    proposal_id: str,
    broker_id: str = Form(...),
    admin_notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Aprovar proposta e direcionar para corretor"""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    proposal.status = ProposalStatus.BROKER_ASSIGNED
    proposal.broker_id = broker_id
    proposal.admin_notes = admin_notes
    proposal.admin_approved_at = datetime.utcnow()
    proposal.broker_assigned_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url="/propostas?status=assigned", status_code=303)


@app.post("/proposta/{proposal_id}/rejeitar")
async def reject_proposal(
    proposal_id: str,
    admin_notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Rejeitar proposta"""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    proposal.status = ProposalStatus.ADMIN_REJECTED
    proposal.admin_notes = admin_notes

    db.commit()

    return RedirectResponse(url="/propostas?status=rejected", status_code=303)


@app.get("/corretores", response_class=HTMLResponse)
async def brokers_list(request: Request, db: Session = Depends(get_db)):
    """Lista de corretores"""
    brokers = db.query(Broker).all()

    return templates.TemplateResponse("corretores.html", {
        "request": request,
        "brokers": brokers
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
