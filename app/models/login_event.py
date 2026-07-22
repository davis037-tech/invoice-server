import uuid
from ..extensions import db


class LoginEvent(db.Model):
    """
    One row per successful login. Email and tenant name are denormalized
    (copied at the time of login) so the admin activity view doesn't need
    joins and still reads correctly even if a user's email changes later.
    """
    __tablename__ = "login_events"

    id           = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    tenant_id    = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    email        = db.Column(db.String, nullable=False)
    tenant_name  = db.Column(db.String, nullable=True)
    created_at   = db.Column(db.DateTime, server_default=db.func.now())
