from uuid import uuid4
from sqlalchemy import Numeric, ForeignKey
from ..extensions import db 

class Settings(db.Model):
    __tablename__ = "settings"
    
    id                 = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id          = db.Column(db.String, ForeignKey("tenants.id"), unique=True) 
    business_name      = db.Column(db.String, nullable=True)
    business_logo      = db.Column(db.String, nullable=True)
    business_address   = db.Column(db.Text, nullable=True)
    primary_color      = db.Column(db.String, default="#C9A84C") 
    currency           = db.Column(db.String(3), default="USD")
    tax_rate           = db.Column(Numeric(5,4), default=0.0)
    payment_info       = db.Column(db.Text, nullable=True)  # legacy free-text, kept for old data
    bank_name          = db.Column(db.String, nullable=True)
    account_name       = db.Column(db.String, nullable=True)
    account_number     = db.Column(db.String, nullable=True)
    routing_number     = db.Column(db.String, nullable=True)  # routing / IBAN / sort code — whatever applies
    swift_code         = db.Column(db.String, nullable=True)
    payment_notes      = db.Column(db.Text, nullable=True)  # anything else the client needs to know
    
    
    def to_dict(self):
      return{
        "id":                  self.id,
        "tenant_id":           self.tenant_id,
        "business_name":      self.business_name,
        "business_logo":       self.business_logo,
        "business_address":    self.business_address,
        "primary_color":       self.primary_color,
        "currency":            self.currency,
        "tax_rate":            float(self.tax_rate),
        "payment_info":        self.payment_info,
        "bank_name":           self.bank_name,
        "account_name":        self.account_name,
        "account_number":      self.account_number,
        "routing_number":      self.routing_number,
        "swift_code":          self.swift_code,
        "payment_notes":       self.payment_notes,
      } 
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
