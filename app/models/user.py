from uuid import uuid4
from enum import Enum 
from sqlalchemy import Enum as SAEnum, ForeignKey  
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db 

class Role(Enum):
    OWNER  = "OWNER"
    ADMIN  = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"

class User(db.Model):
    __tablename__ = "users"
    
    id             = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id      = db.Column(db.String, ForeignKey("tenants.id"), nullable=False)
    email          = db.Column(db.String, unique=True, nullable=False)
    password_hash  = db.Column(db.String, nullable=False)
    role           = db.Column(SAEnum(Role), default=Role.MEMBER)
    is_superadmin  = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at  = db.Column(db.DateTime, nullable=True)
    created_at     = db.Column(db.DateTime, server_default=db.func.now())
    
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
          "id":           self.id,
          "email":        self.email,
          "role":         self.role.value,
          "tenant_id":    self.tenant_id,
          "is_superadmin": self.is_superadmin,
          "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
          "created_at":   self.created_at.isoformat()
        }

















