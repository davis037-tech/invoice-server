from enum import Enum 
from uuid import uuid4
from ..extensions import db 
from sqlalchemy import Enum as SAEnum

class Plan(Enum):
    FREE = "FREE"
    PRO  = "PRO"
    TEAM = "TEAM"
    
class Tenant(db.Model):
    __tablename__ = "tenants"
    
    id         = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    name       = db.Column(db.String, nullable=False)
    slug       = db.Column(db.String, unique=True, nullable=False)
    stripe_id  = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    plan       = db.Column(SAEnum(Plan), default=Plan.FREE)
    users      = db.relationship("User", backref="tenant", lazy=True)
    clients    = db.relationship("Client", backref="tenant", lazy=True)
    invoices   = db.relationship("Invoice", backref="tenant", lazy=True)
    settings   = db.relationship("Settings", backref="tenant", uselist=False)
    














