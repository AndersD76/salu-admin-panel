"""
Salu Imóveis - Painel Administrativo
"""
from fastapi import FastAPI, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Boolean, Enum as SQLEnum, Integer, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import os
import enum
from datetime import datetime, timedelta
from typing import Optional

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

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


class DocumentType(enum.Enum):
    RG = "RG"
    CPF = "CPF"
    COMPROVANTE_RENDA = "COMPROVANTE_RENDA"
    COMPROVANTE_RESIDENCIA = "COMPROVANTE_RESIDENCIA"
    IMPOSTO_RENDA = "IMPOSTO_RENDA"
    OUTROS = "OUTROS"


class DocumentStatus(enum.Enum):
    UPLOADED = "UPLOADED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VisitStatus(enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserRole(enum.Enum):
    USER = "USER"
    OWNER = "OWNER"
    BROKER = "BROKER"
    ADMIN = "ADMIN"


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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    proposal_id = Column(String, nullable=True)
    contract_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Visit(Base):
    __tablename__ = "visits"
    id = Column(String, primary_key=True)
    property_id = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    broker_id = Column(String, nullable=True)
    visitor_name = Column(String, nullable=False)
    visitor_email = Column(String, nullable=False)
    visitor_phone = Column(String, nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    message = Column(Text, nullable=True)
    visit_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    broker_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)
    email_verified = Column(DateTime, nullable=True)
    password = Column(String, nullable=True)
    image = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    cpf = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PropertyView(Base):
    __tablename__ = "property_views"
    id = Column(String, primary_key=True)
    property_id = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    referer = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    property_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(String, primary_key=True)
    property_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Building Models (espelho do portal)
class Building(Base):
    __tablename__ = "buildings"
    id = Column(String, primary_key=True)
    external_code = Column(String, nullable=True)
    name = Column(String, nullable=False)
    building_type = Column(String, nullable=True)
    street_type = Column(String, nullable=True)
    address = Column(String, nullable=True)
    number = Column(String, nullable=True)
    city = Column(String, nullable=True)
    neighborhood = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    total_floors = Column(Integer, default=0)
    total_units = Column(Integer, default=0)
    construction_year = Column(Integer, nullable=True)
    builder = Column(String, nullable=True)
    developer = Column(String, nullable=True)
    architect = Column(String, nullable=True)
    phase = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    property_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class BuildingPhoto(Base):
    __tablename__ = "building_photos"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    photo_type = Column(String, nullable=True)
    caption = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    order = Column(Integer, default=0)


class BuildingAmenity(Base):
    __tablename__ = "building_amenities"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=False)
    amenity_name = Column(String, nullable=False)
    amenity_value = Column(String, nullable=True)
    amenity_type = Column(String, nullable=True)


class BuildingUnit(Base):
    __tablename__ = "building_units"
    id = Column(String, primary_key=True)
    building_id = Column(String, nullable=False)
    unit_type = Column(String, nullable=True)
    bedrooms = Column(Integer, default=0)
    suites = Column(Integer, default=0)
    bathrooms = Column(Integer, default=0)
    parking_covered = Column(Integer, default=0)
    private_area = Column(Float, nullable=True)
    total_area = Column(Float, nullable=True)
    for_sale = Column(Boolean, default=True)
    for_rent = Column(Boolean, default=False)
    price = Column(Float, nullable=True)


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
    pending_proposals = db.query(Proposal).filter(
        Proposal.status == ProposalStatus.PENDING
    ).count()

    pending_docs = db.query(Document).filter(
        Document.status == 'UPLOADED'
    ).count()

    today = datetime.utcnow().date()
    today_visits = db.query(Visit).filter(
        func.date(Visit.scheduled_date) == today
    ).count()

    total_brokers = db.query(Broker).filter(
        Broker.is_active.is_(True)
    ).count()

    total_properties = db.query(Property).filter(
        Property.is_active.is_(True)
    ).count()

    # Recent proposals
    recent_proposals = db.query(Proposal).order_by(
        Proposal.created_at.desc()
    ).limit(5).all()

    # Recent documents
    recent_documents = db.query(Document).filter(
        Document.status == 'UPLOADED'
    ).order_by(Document.created_at.desc()).limit(5).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "pending_proposals": pending_proposals,
            "pending_documents": pending_docs,
            "today_visits": today_visits,
            "total_brokers": total_brokers,
            "total_properties": total_properties
        },
        "recent_proposals": recent_proposals,
        "recent_documents": recent_documents
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


# ===== DOCUMENTOS =====

@app.get("/documentos", response_class=HTMLResponse)
async def documents_list(
    request: Request,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Lista de documentos"""
    query = db.query(Document)

    if status:
        status_map = {
            "pending": "UPLOADED",
            "approved": "APPROVED",
            "rejected": "REJECTED"
        }
        if status in status_map:
            query = query.filter(Document.status == status_map[status])

    documents = query.order_by(Document.created_at.desc()).all()

    # Get proposal info for each document
    document_data = []
    for doc in documents:
        proposal = db.query(Proposal).filter(
            Proposal.id == doc.proposal_id
        ).first()
        document_data.append({
            "document": doc,
            "proposal": proposal
        })

    return templates.TemplateResponse("documentos.html", {
        "request": request,
        "documents": document_data,
        "current_status": status
    })


@app.get("/documento/{document_id}", response_class=HTMLResponse)
async def document_detail(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """Detalhes do documento"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    proposal = db.query(Proposal).filter(
        Proposal.id == document.proposal_id
    ).first()

    return templates.TemplateResponse("documento_detalhe.html", {
        "request": request,
        "document": document,
        "proposal": proposal
    })


@app.post("/documento/{document_id}/aprovar")
async def approve_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Aprovar documento"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    document.status = "APPROVED"
    document.reviewed_at = datetime.utcnow()
    document.reviewed_by = "admin"

    db.commit()

    return RedirectResponse(url="/documentos?status=approved", status_code=303)


@app.post("/documento/{document_id}/rejeitar")
async def reject_document(
    document_id: str,
    rejection_reason: str = Form(...),
    db: Session = Depends(get_db)
):
    """Rejeitar documento"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    document.status = "REJECTED"
    document.rejection_reason = rejection_reason
    document.reviewed_at = datetime.utcnow()
    document.reviewed_by = "admin"

    db.commit()

    return RedirectResponse(url="/documentos?status=rejected", status_code=303)


# ===== IMÓVEIS =====

@app.get("/imoveis", response_class=HTMLResponse)
async def properties_list(
    request: Request,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Lista de imóveis"""
    query = db.query(Property)

    if status == "active":
        query = query.filter(Property.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(Property.is_active.is_(False))

    properties = query.order_by(Property.created_at.desc()).all()

    return templates.TemplateResponse("imoveis.html", {
        "request": request,
        "properties": properties,
        "current_status": status
    })


@app.get("/imovel/{property_id}", response_class=HTMLResponse)
async def property_detail(
    request: Request,
    property_id: str,
    db: Session = Depends(get_db)
):
    """Detalhes do imóvel"""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    return templates.TemplateResponse("imovel_detalhe.html", {
        "request": request,
        "property": property
    })


@app.post("/imovel/{property_id}/toggle-status")
async def toggle_property_status(
    property_id: str,
    db: Session = Depends(get_db)
):
    """Ativar/Desativar imóvel"""
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    property.is_active = not property.is_active

    db.commit()

    return RedirectResponse(url="/imoveis", status_code=303)


# ===== VISITAS =====

@app.get("/visitas", response_class=HTMLResponse)
async def visits_list(
    request: Request,
    date: str = None,
    broker_id: str = None,
    db: Session = Depends(get_db)
):
    """Lista de visitas"""
    query = db.query(Visit)

    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(func.date(Visit.scheduled_date) == date_obj)
        except ValueError:
            pass

    if broker_id:
        query = query.filter(Visit.broker_id == broker_id)

    visits = query.order_by(Visit.scheduled_date.asc()).all()

    # Get property and broker info
    visit_data = []
    for visit in visits:
        property = db.query(Property).filter(
            Property.id == visit.property_id
        ).first()
        broker = None
        if visit.broker_id:
            broker = db.query(Broker).filter(
                Broker.id == visit.broker_id
            ).first()
        visit_data.append({
            "visit": visit,
            "property": property,
            "broker": broker
        })

    brokers = db.query(Broker).filter(Broker.is_active.is_(True)).all()

    return templates.TemplateResponse("visitas.html", {
        "request": request,
        "visits": visit_data,
        "brokers": brokers,
        "current_date": date,
        "current_broker": broker_id
    })


@app.post("/visita/{visit_id}/confirmar")
async def confirm_visit(
    visit_id: str,
    db: Session = Depends(get_db)
):
    """Confirmar visita"""
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visita não encontrada")

    visit.status = "CONFIRMED"
    visit.confirmed_at = datetime.utcnow()
    visit.updated_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url="/visitas", status_code=303)


@app.post("/visita/{visit_id}/cancelar")
async def cancel_visit(
    visit_id: str,
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Cancelar visita"""
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visita não encontrada")

    visit.status = "CANCELLED"
    visit.cancelled_at = datetime.utcnow()
    if notes:
        visit.cancellation_reason = notes
    visit.updated_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url="/visitas", status_code=303)


# ===== USUÁRIOS =====

@app.get("/usuarios", response_class=HTMLResponse)
async def users_list(
    request: Request,
    role: str = None,
    db: Session = Depends(get_db)
):
    """Lista de usuários"""
    query = db.query(User)

    if role:
        role_map = {
            "user": UserRole.USER,
            "owner": UserRole.OWNER,
            "broker": UserRole.BROKER,
            "admin": UserRole.ADMIN
        }
        if role in role_map:
            query = query.filter(User.role == role_map[role])

    users = query.order_by(User.created_at.desc()).all()

    return templates.TemplateResponse("usuarios.html", {
        "request": request,
        "users": users,
        "current_role": role
    })


@app.get("/usuario/{user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    user_id: str,
    db: Session = Depends(get_db)
):
    """Detalhes do usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Get user proposals
    proposals = db.query(Proposal).filter(
        Proposal.email == user.email
    ).all()

    return templates.TemplateResponse("usuario_detalhe.html", {
        "request": request,
        "user": user,
        "proposals": proposals
    })


@app.post("/usuario/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Ativar/Desativar usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url="/usuarios", status_code=303)


# ===== RELATÓRIOS =====

@app.get("/relatorios", response_class=HTMLResponse)
async def reports(request: Request, db: Session = Depends(get_db)):
    """Relatórios e métricas completas"""
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)

    # === PROPOSALS METRICS ===
    proposal_stats = {
        "pending": db.query(Proposal).filter(Proposal.status == ProposalStatus.PENDING).count(),
        "assigned": db.query(Proposal).filter(Proposal.status == ProposalStatus.BROKER_ASSIGNED).count(),
        "approved": db.query(Proposal).filter(Proposal.status == ProposalStatus.APPROVED).count(),
        "rejected": db.query(Proposal).filter(Proposal.status == ProposalStatus.ADMIN_REJECTED).count()
    }

    proposal_by_type = {
        "buy": db.query(Proposal).filter(Proposal.type == ProposalType.BUY).count(),
        "rent": db.query(Proposal).filter(Proposal.type == ProposalType.RENT).count(),
        "sell": db.query(Proposal).filter(Proposal.type == ProposalType.SELL).count()
    }

    # === PROPERTY METRICS ===
    total_properties = db.query(Property).count()
    active_properties = db.query(Property).filter(Property.is_active.is_(True)).count()

    properties_by_type = db.query(
        Property.property_type, func.count(Property.id)
    ).filter(Property.is_active.is_(True)).group_by(Property.property_type).all()

    properties_by_city = db.query(
        Property.city, func.count(Property.id)
    ).filter(Property.is_active.is_(True)).group_by(Property.city).order_by(
        func.count(Property.id).desc()
    ).limit(10).all()

    # Most viewed properties (last 30 days)
    most_viewed_properties = db.query(
        Property.id, Property.title, Property.city, Property.neighborhood,
        Property.sale_price, Property.rental_price,
        func.count(PropertyView.id).label('view_count')
    ).join(PropertyView, Property.id == PropertyView.property_id).filter(
        PropertyView.created_at >= thirty_days_ago
    ).group_by(Property.id).order_by(func.count(PropertyView.id).desc()).limit(10).all()

    # Total views metrics
    total_views_30d = db.query(PropertyView).filter(PropertyView.created_at >= thirty_days_ago).count()
    total_views_7d = db.query(PropertyView).filter(PropertyView.created_at >= seven_days_ago).count()
    total_views_today = db.query(PropertyView).filter(func.date(PropertyView.created_at) == today).count()

    # Views per day (last 30 days) for chart
    views_per_day = db.query(
        func.date(PropertyView.created_at).label('date'),
        func.count(PropertyView.id).label('count')
    ).filter(PropertyView.created_at >= thirty_days_ago).group_by(
        func.date(PropertyView.created_at)
    ).order_by(func.date(PropertyView.created_at)).all()

    # === USER METRICS ===
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()

    users_by_role = {
        "admin": db.query(User).filter(User.role == UserRole.ADMIN).count(),
        "broker": db.query(User).filter(User.role == UserRole.BROKER).count(),
        "owner": db.query(User).filter(User.role == UserRole.OWNER).count(),
        "user": db.query(User).filter(User.role == UserRole.USER).count()
    }

    new_users_30d = db.query(User).filter(User.created_at >= thirty_days_ago).count()

    users_per_day = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago).group_by(
        func.date(User.created_at)
    ).order_by(func.date(User.created_at)).all()

    # === VISIT METRICS ===
    total_visits = db.query(Visit).count()
    # Support both uppercase (old) and lowercase (new) status values
    visits_scheduled = db.query(Visit).filter(Visit.status.in_(['SCHEDULED', 'pending'])).count()
    visits_confirmed = db.query(Visit).filter(Visit.status.in_(['CONFIRMED', 'confirmed'])).count()
    visits_completed = db.query(Visit).filter(Visit.status.in_(['COMPLETED', 'completed'])).count()
    visits_cancelled = db.query(Visit).filter(Visit.status.in_(['CANCELLED', 'cancelled'])).count()
    visits_today = db.query(Visit).filter(func.date(Visit.scheduled_date) == today).count()
    visits_week = db.query(Visit).filter(Visit.scheduled_date >= seven_days_ago).count()

    # === CONTACT & FAVORITES METRICS ===
    total_contacts = db.query(Contact).count()
    contacts_30d = db.query(Contact).filter(Contact.created_at >= thirty_days_ago).count()
    total_favorites = db.query(Favorite).count()
    favorites_30d = db.query(Favorite).filter(Favorite.created_at >= thirty_days_ago).count()

    most_favorited = db.query(
        Property.id, Property.title, Property.city,
        func.count(Favorite.id).label('favorite_count')
    ).join(Favorite, Property.id == Favorite.property_id).group_by(
        Property.id
    ).order_by(func.count(Favorite.id).desc()).limit(10).all()

    # === BROKER PERFORMANCE ===
    brokers = db.query(Broker).filter(Broker.is_active.is_(True)).all()
    broker_stats = []
    for broker in brokers:
        proposals_count = db.query(Proposal).filter(Proposal.broker_id == broker.id).count()
        approved_count = db.query(Proposal).filter(
            Proposal.broker_id == broker.id, Proposal.status == ProposalStatus.APPROVED
        ).count()
        visits_count = db.query(Visit).filter(Visit.broker_id == broker.id).count()
        completed_visits = db.query(Visit).filter(
            Visit.broker_id == broker.id, Visit.status == 'COMPLETED'
        ).count()
        conversion_rate = (approved_count / proposals_count * 100) if proposals_count > 0 else 0

        broker_stats.append({
            "broker": broker,
            "proposals_count": proposals_count,
            "approved_count": approved_count,
            "visits_count": visits_count,
            "completed_visits": completed_visits,
            "conversion_rate": round(conversion_rate, 1)
        })
    broker_stats.sort(key=lambda x: x["proposals_count"], reverse=True)

    # === CRM METRICS ===
    try:
        total_leads = db.query(CRMLead).filter(CRMLead.is_active.is_(True)).count()
        leads_new = db.query(CRMLead).filter(CRMLead.status == 'NOVO').count()
        leads_converted = db.query(CRMLead).filter(CRMLead.status == 'CONVERTIDO').count()
        leads_lost = db.query(CRMLead).filter(CRMLead.status == 'PERDIDO').count()
        crm_conversion_rate = (leads_converted / total_leads * 100) if total_leads > 0 else 0
        crm_stats = {
            "total_leads": total_leads,
            "leads_new": leads_new,
            "leads_converted": leads_converted,
            "leads_lost": leads_lost,
            "conversion_rate": round(crm_conversion_rate, 1)
        }
    except:
        crm_stats = None

    return templates.TemplateResponse("relatorios.html", {
        "request": request,
        "active": "relatorios",
        "proposal_stats": proposal_stats,
        "proposal_by_type": proposal_by_type,
        "total_properties": total_properties,
        "active_properties": active_properties,
        "properties_by_type": [list(p) for p in properties_by_type],
        "properties_by_city": [list(c) for c in properties_by_city],
        "most_viewed_properties": most_viewed_properties,
        "total_views_30d": total_views_30d,
        "total_views_7d": total_views_7d,
        "total_views_today": total_views_today,
        "views_per_day": [(str(v[0]), v[1]) for v in views_per_day],
        "total_users": total_users,
        "active_users": active_users,
        "users_by_role": users_by_role,
        "new_users_30d": new_users_30d,
        "users_per_day": [(str(u[0]), u[1]) for u in users_per_day],
        "total_visits": total_visits,
        "visits_scheduled": visits_scheduled,
        "visits_confirmed": visits_confirmed,
        "visits_completed": visits_completed,
        "visits_cancelled": visits_cancelled,
        "visits_today": visits_today,
        "visits_week": visits_week,
        "total_contacts": total_contacts,
        "contacts_30d": contacts_30d,
        "total_favorites": total_favorites,
        "favorites_30d": favorites_30d,
        "most_favorited": [(f[0], f[1], f[2], f[3]) for f in most_favorited],
        "broker_stats": broker_stats[:10],
        "crm_stats": crm_stats
    })


# ===== EMPREENDIMENTOS =====

@app.get("/empreendimentos", response_class=HTMLResponse)
async def buildings_list(
    request: Request,
    status: str = None,
    city: str = None,
    db: Session = Depends(get_db)
):
    """Lista de empreendimentos"""
    query = db.query(Building)

    if status == "active":
        query = query.filter(Building.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(Building.is_active.is_(False))
    elif status == "featured":
        query = query.filter(Building.is_featured.is_(True))

    if city:
        query = query.filter(Building.city.ilike(f'%{city}%'))

    buildings = query.order_by(Building.name).all()

    # Get cities for filter
    cities = db.query(Building.city).filter(
        Building.city.isnot(None)
    ).distinct().order_by(Building.city).all()
    cities = [c[0] for c in cities if c[0]]

    # Get stats
    total_buildings = db.query(Building).count()
    active_buildings = db.query(Building).filter(Building.is_active.is_(True)).count()
    featured_buildings = db.query(Building).filter(Building.is_featured.is_(True)).count()

    return templates.TemplateResponse("empreendimentos.html", {
        "request": request,
        "buildings": buildings,
        "cities": cities,
        "current_status": status,
        "current_city": city,
        "stats": {
            "total": total_buildings,
            "active": active_buildings,
            "featured": featured_buildings
        }
    })


@app.get("/empreendimento/{building_id}", response_class=HTMLResponse)
async def building_detail(
    request: Request,
    building_id: str,
    db: Session = Depends(get_db)
):
    """Detalhes do empreendimento"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

    # Get photos
    photos = db.query(BuildingPhoto).filter(
        BuildingPhoto.building_id == building_id
    ).order_by(BuildingPhoto.order).all()

    # Get amenities
    amenities = db.query(BuildingAmenity).filter(
        BuildingAmenity.building_id == building_id
    ).all()

    # Get units
    units = db.query(BuildingUnit).filter(
        BuildingUnit.building_id == building_id
    ).all()

    # Get properties in this building
    properties = db.query(Property).filter(
        Property.is_active.is_(True)
    ).limit(10).all()  # Simplified - would need building_id on Property

    return templates.TemplateResponse("empreendimento_detalhe.html", {
        "request": request,
        "building": building,
        "photos": photos,
        "amenities": amenities,
        "units": units,
        "properties": properties
    })


@app.post("/empreendimento/{building_id}/toggle-status")
async def toggle_building_status(
    building_id: str,
    db: Session = Depends(get_db)
):
    """Ativar/Desativar empreendimento"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

    building.is_active = not building.is_active
    building.updated_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url="/empreendimentos", status_code=303)


@app.post("/empreendimento/{building_id}/toggle-featured")
async def toggle_building_featured(
    building_id: str,
    db: Session = Depends(get_db)
):
    """Destacar/Remover destaque do empreendimento"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

    building.is_featured = not building.is_featured
    building.updated_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url="/empreendimentos", status_code=303)


@app.post("/empreendimento/{building_id}/editar")
async def update_building(
    building_id: str,
    name: str = Form(...),
    building_type: str = Form(None),
    description: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    neighborhood: str = Form(None),
    state: str = Form(None),
    total_floors: int = Form(0),
    total_units: int = Form(0),
    construction_year: int = Form(None),
    builder: str = Form(None),
    developer: str = Form(None),
    min_price: float = Form(None),
    max_price: float = Form(None),
    db: Session = Depends(get_db)
):
    """Atualizar empreendimento"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Empreendimento não encontrado")

    building.name = name
    building.building_type = building_type
    building.description = description
    building.address = address
    building.city = city
    building.neighborhood = neighborhood
    building.state = state
    building.total_floors = total_floors or 0
    building.total_units = total_units or 0
    building.construction_year = construction_year
    building.builder = builder
    building.developer = developer
    building.min_price = min_price
    building.max_price = max_price
    building.updated_at = datetime.utcnow()

    db.commit()

    return RedirectResponse(url=f"/empreendimento/{building_id}", status_code=303)


# ===== CRM MODELS =====

class CRMLead(Base):
    __tablename__ = "crm_leads"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    source = Column(String)
    interest_type = Column(String)
    property_type = Column(String)
    budget_min = Column(Float)
    budget_max = Column(Float)
    city = Column(String)
    neighborhood = Column(String)
    notes = Column(Text)
    status = Column(String, default='NOVO')
    broker_id = Column(String)
    property_id = Column(String)
    user_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    converted_at = Column(DateTime)
    is_active = Column(Boolean, default=True)


class CRMInteraction(Base):
    __tablename__ = "crm_interactions"
    id = Column(String, primary_key=True)
    lead_id = Column(String)
    user_id = Column(String)
    broker_id = Column(String)
    type = Column(String, nullable=False)
    channel = Column(String)
    subject = Column(String)
    description = Column(Text)
    outcome = Column(String)
    next_action = Column(String)
    next_action_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)


class CRMTask(Base):
    __tablename__ = "crm_tasks"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String)
    priority = Column(String, default='NORMAL')
    status = Column(String, default='PENDENTE')
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    lead_id = Column(String)
    user_id = Column(String)
    broker_id = Column(String)
    property_id = Column(String)
    assigned_to = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)


class CRMPipelineStage(Base):
    __tablename__ = "crm_pipeline_stages"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    color = Column(String)
    position = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


# ===== CRM ROUTES =====

@app.get("/crm", response_class=HTMLResponse)
async def crm_dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard do CRM"""
    # Estatísticas
    total_leads = db.query(CRMLead).filter(CRMLead.is_active.is_(True)).count()
    leads_novos = db.query(CRMLead).filter(CRMLead.status == 'NOVO').count()
    leads_qualificados = db.query(CRMLead).filter(CRMLead.status == 'QUALIFICADO').count()
    leads_convertidos = db.query(CRMLead).filter(CRMLead.status == 'CONVERTIDO').count()

    tarefas_pendentes = db.query(CRMTask).filter(CRMTask.status == 'PENDENTE').count()
    tarefas_hoje = db.query(CRMTask).filter(
        func.date(CRMTask.due_date) == datetime.utcnow().date(),
        CRMTask.status == 'PENDENTE'
    ).count()

    # Leads recentes
    leads_recentes = db.query(CRMLead).filter(
        CRMLead.is_active.is_(True)
    ).order_by(CRMLead.created_at.desc()).limit(5).all()

    # Tarefas para hoje
    tarefas_hoje_list = db.query(CRMTask).filter(
        func.date(CRMTask.due_date) == datetime.utcnow().date(),
        CRMTask.status == 'PENDENTE'
    ).order_by(CRMTask.due_date).all()

    return templates.TemplateResponse("crm/dashboard.html", {
        "request": request,
        "total_leads": total_leads,
        "leads_novos": leads_novos,
        "leads_qualificados": leads_qualificados,
        "leads_convertidos": leads_convertidos,
        "tarefas_pendentes": tarefas_pendentes,
        "tarefas_hoje": tarefas_hoje,
        "leads_recentes": leads_recentes,
        "tarefas_hoje_list": tarefas_hoje_list
    })


@app.get("/crm/leads", response_class=HTMLResponse)
async def crm_leads_list(
    request: Request,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Lista de leads"""
    query = db.query(CRMLead).filter(CRMLead.is_active.is_(True))

    if status:
        query = query.filter(CRMLead.status == status.upper())

    leads = query.order_by(CRMLead.created_at.desc()).all()

    # Buscar corretores para associar
    brokers = db.query(Broker).filter(Broker.is_active.is_(True)).all()

    return templates.TemplateResponse("crm/leads.html", {
        "request": request,
        "leads": leads,
        "brokers": brokers,
        "current_status": status
    })


@app.get("/crm/lead/{lead_id}", response_class=HTMLResponse)
async def crm_lead_detail(
    request: Request,
    lead_id: str,
    db: Session = Depends(get_db)
):
    """Detalhes do lead"""
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Interações do lead
    interactions = db.query(CRMInteraction).filter(
        CRMInteraction.lead_id == lead_id
    ).order_by(CRMInteraction.created_at.desc()).all()

    # Tarefas do lead
    tasks = db.query(CRMTask).filter(
        CRMTask.lead_id == lead_id
    ).order_by(CRMTask.due_date).all()

    # Corretores para atribuição
    brokers = db.query(Broker).filter(Broker.is_active.is_(True)).all()

    return templates.TemplateResponse("crm/lead_detalhe.html", {
        "request": request,
        "lead": lead,
        "interactions": interactions,
        "tasks": tasks,
        "brokers": brokers
    })


@app.post("/crm/lead/novo")
async def crm_lead_create(
    request: Request,
    name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    source: str = Form(None),
    interest_type: str = Form(None),
    property_type: str = Form(None),
    budget_min: float = Form(None),
    budget_max: float = Form(None),
    city: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Criar novo lead"""
    import uuid
    lead = CRMLead(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        phone=phone,
        source=source,
        interest_type=interest_type,
        property_type=property_type,
        budget_min=budget_min,
        budget_max=budget_max,
        city=city,
        notes=notes,
        status='NOVO'
    )
    db.add(lead)
    db.commit()
    return RedirectResponse(url="/crm/leads", status_code=303)


@app.post("/crm/lead/{lead_id}/status")
async def crm_lead_update_status(
    lead_id: str,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Atualizar status do lead"""
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if lead:
        lead.status = status.upper()
        lead.updated_at = datetime.utcnow()
        if status.upper() == 'CONVERTIDO':
            lead.converted_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url=f"/crm/lead/{lead_id}", status_code=303)


@app.post("/crm/lead/{lead_id}/interacao")
async def crm_add_interaction(
    lead_id: str,
    type: str = Form(...),
    channel: str = Form(None),
    subject: str = Form(None),
    description: str = Form(None),
    outcome: str = Form(None),
    next_action: str = Form(None),
    db: Session = Depends(get_db)
):
    """Adicionar interação ao lead"""
    import uuid
    interaction = CRMInteraction(
        id=str(uuid.uuid4()),
        lead_id=lead_id,
        type=type,
        channel=channel,
        subject=subject,
        description=description,
        outcome=outcome,
        next_action=next_action
    )
    db.add(interaction)
    db.commit()
    return RedirectResponse(url=f"/crm/lead/{lead_id}", status_code=303)


@app.get("/crm/pipeline", response_class=HTMLResponse)
async def crm_pipeline(request: Request, db: Session = Depends(get_db)):
    """Pipeline Kanban de vendas"""
    stages = db.query(CRMPipelineStage).filter(
        CRMPipelineStage.is_active.is_(True)
    ).order_by(CRMPipelineStage.position).all()

    # Buscar leads por stage (usando status do lead para associar)
    stage_status_map = {
        'Novo Lead': 'NOVO',
        'Primeiro Contato': 'EM_CONTATO',
        'Qualificado': 'QUALIFICADO',
        'Visita Agendada': 'VISITA_AGENDADA',
        'Proposta Enviada': 'PROPOSTA_ENVIADA',
        'Negociação': 'NEGOCIANDO',
        'Fechado Ganho': 'CONVERTIDO',
        'Fechado Perdido': 'PERDIDO'
    }

    # Criar estrutura com stages contendo leads
    stages_with_leads = []
    for stage in stages:
        status = stage_status_map.get(stage.name, stage.name.upper().replace(' ', '_'))
        leads = db.query(CRMLead).filter(
            CRMLead.status == status,
            CRMLead.is_active.is_(True)
        ).order_by(CRMLead.created_at.desc()).all()
        stage.leads = leads
        stages_with_leads.append(stage)

    # Estatísticas
    total_leads = db.query(CRMLead).filter(CRMLead.is_active.is_(True)).count()
    leads_negociacao = db.query(CRMLead).filter(CRMLead.status == 'NEGOCIANDO').count()
    leads_fechados = db.query(CRMLead).filter(CRMLead.status == 'CONVERTIDO').count()
    taxa_conversao = round((leads_fechados / total_leads * 100) if total_leads > 0 else 0, 1)

    return templates.TemplateResponse("crm/pipeline.html", {
        "request": request,
        "stages": stages_with_leads,
        "total_leads": total_leads,
        "leads_negociacao": leads_negociacao,
        "leads_fechados": leads_fechados,
        "taxa_conversao": taxa_conversao
    })


@app.post("/crm/lead/{lead_id}/stage")
async def crm_lead_update_stage(
    lead_id: str,
    stage_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Atualizar stage do lead (drag-and-drop no pipeline)"""
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # Buscar o stage para obter o status correspondente
    stage = db.query(CRMPipelineStage).filter(CRMPipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage não encontrado")

    # Mapear stage name para status
    stage_status_map = {
        'Novo Lead': 'NOVO',
        'Primeiro Contato': 'EM_CONTATO',
        'Qualificado': 'QUALIFICADO',
        'Visita Agendada': 'VISITA_AGENDADA',
        'Proposta Enviada': 'PROPOSTA_ENVIADA',
        'Negociação': 'NEGOCIANDO',
        'Fechado Ganho': 'CONVERTIDO',
        'Fechado Perdido': 'PERDIDO'
    }

    new_status = stage_status_map.get(stage.name, stage.name.upper().replace(' ', '_'))
    lead.status = new_status
    lead.updated_at = datetime.utcnow()

    if new_status == 'CONVERTIDO':
        lead.converted_at = datetime.utcnow()

    db.commit()

    return JSONResponse(content={"success": True, "status": new_status})


@app.get("/crm/tarefas", response_class=HTMLResponse)
async def crm_tasks_list(
    request: Request,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Lista de tarefas"""
    query = db.query(CRMTask)

    if status:
        query = query.filter(CRMTask.status == status.upper())

    tasks = query.order_by(CRMTask.due_date).all()

    # Tarefas de hoje
    today = datetime.utcnow().date()
    tasks_today = db.query(CRMTask).filter(
        func.date(CRMTask.due_date) == today,
        CRMTask.status == 'PENDENTE'
    ).count()

    # Tarefas atrasadas
    tasks_overdue = db.query(CRMTask).filter(
        CRMTask.due_date < datetime.utcnow(),
        CRMTask.status == 'PENDENTE'
    ).count()

    return templates.TemplateResponse("crm/tarefas.html", {
        "request": request,
        "tasks": tasks,
        "tasks_today": tasks_today,
        "tasks_overdue": tasks_overdue,
        "current_status": status,
        "now": datetime.utcnow()
    })


@app.post("/crm/tarefa/nova")
async def crm_task_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    type: str = Form(None),
    priority: str = Form('NORMAL'),
    due_date: str = Form(None),
    lead_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """Criar nova tarefa"""
    import uuid
    task = CRMTask(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        type=type,
        priority=priority,
        due_date=datetime.strptime(due_date, '%Y-%m-%dT%H:%M') if due_date else None,
        lead_id=lead_id if lead_id else None,
        status='PENDENTE'
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url="/crm/tarefas", status_code=303)


@app.post("/crm/tarefa/{task_id}/concluir")
async def crm_task_complete(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Marcar tarefa como concluída"""
    task = db.query(CRMTask).filter(CRMTask.id == task_id).first()
    if task:
        task.status = 'CONCLUIDA'
        task.completed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/crm/tarefas", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
