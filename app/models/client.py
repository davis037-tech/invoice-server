from uuid import uuid4
from ..extensions import db 
from sqlalchemy import ForeignKey


class Client(db.Model):
    __tablename__ = "clients"
  
    id           = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id    = db.Column(db.String, ForeignKey("tenants.id"), nullable=False)
    name         = db.Column(db.String, nullable=False)
    email        = db.Column(db.String, nullable=False)
    phone        = db.Column(db.String, nullable=True)
    address      = db.Column(db.String, nullable=True)
    created_at   = db.Column(db.DateTime, server_default=db.func.now())
    invoices     = db.relationship("Invoice", backref="client", lazy=True)
    
    def to_dict(self):
        return {
        "id":          self.id,
        "tenant_id":   self.tenant_id,
        "name":        self.name,
        "email":       self.email,
        "phone":       self.phone,
        "address":     self.address,
        "created_at":  self.created_at.isoformat()
      }
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    