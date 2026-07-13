from enum import Enum 
from uuid import uuid4
from sqlalchemy import Enum as SAEnum, Numeric, ForeignKey, JSON  
from ..extensions import db 


class InvoiceStatus(Enum):
    DRAFT      = "DRAFT"
    SENT       = "SENT"
    PAID       = "PAID"
    OVERDUE    = "OVERDUE"
    CANCELLED  = "CANCELLED"
  

class Invoice(db.Model):
    __tablename__ = "invoices" 
    
    id                = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id         = db.Column(db.String, ForeignKey("tenants.id"), nullable=False)
    client_id         = db.Column(db.String, ForeignKey("clients.id"), nullable=True)
    client_name        = db.Column(db.String, nullable=False)
    client_email       = db.Column(db.String, nullable=False)
    client_address     = db.Column(db.Text, nullable=True)
    number             = db.Column(db.String, nullable=False)
    items              = db.Column(JSON, nullable=False)
    subtotal           = db.Column(Numeric(10,2), nullable=False)
    tax_rate           = db.Column(Numeric(5,4), default=0.0)
    tax_amount         = db.Column(Numeric(10,2), nullable=False)
    total              = db.Column(Numeric(10,2), nullable=False)
    currency           = db.Column(db.String(3), default="USD")
    issue_date         = db.Column(db.DateTime, server_default=db.func.now())
    due_date           = db.Column(db.DateTime, nullable=True)
    payment_terms      = db.Column(db.Integer, default=30)
    status             = db.Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    public_token       = db.Column(db.String, unique=True, nullable=True)
    payment_url = db.Column(db.String, nullable=True)
    notes              = db.Column(db.Text, nullable=True)
    payment_proof_note      = db.Column(db.Text, nullable=True)
    payment_proof_image     = db.Column(db.Text, nullable=True)  # base64 data URI of a receipt photo
    payment_proof_submitted_at = db.Column(db.DateTime, nullable=True)
    paid_at            = db.Column(db.DateTime, nullable=True)
    last_reminder_sent_at = db.Column(db.DateTime, nullable=True)
    created_at         = db.Column(db.DateTime, server_default=db.func.now())
    
    def to_dict(self):
        return{
          "id":                 self.id,
          "tenant_id":          self.tenant_id,
          "client_id":          self.client_id,
          "client_name":        self.client_name,
          "client_email":       self.client_email,
          "client_address":     self.client_address,
          "number":             self.number,
          "items":              self.items,
          "subtotal":           float(self.subtotal),
          "tax_rate":           float(self.tax_rate), 
          "tax_amount":         float(self.tax_amount),
          "total":              float(self.total),
          "currency":           self.currency,
          "issue_date":         self.issue_date.isoformat(),
          "due_date":           self.due_date.isoformat() if self.due_date else None,
          "payment_terms":      self.payment_terms,
          "status":             self.status.value,
          "public_token":       self.public_token,
          "payment_url":        self.payment_url,
          "notes":              self.notes,
          "payment_proof_note":         self.payment_proof_note,
          "payment_proof_image":        self.payment_proof_image,
          "payment_proof_submitted_at": self.payment_proof_submitted_at.isoformat() if self.payment_proof_submitted_at else None,
          "paid_at":            self.paid_at.isoformat() if self.paid_at else None,
          "last_reminder_sent_at": self.last_reminder_sent_at.isoformat() if self.last_reminder_sent_at else None,
          "created_at":         self.created_at.isoformat()
        }
      
    
   
   

























