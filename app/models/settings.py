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
    payment_info       = db.Column(db.Text, nullable=True)
    
    
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
        "payment_info":        self.payment_info
      } 
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
