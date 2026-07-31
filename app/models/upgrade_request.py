import uuid
from ..extensions import db


class UpgradeRequest(db.Model):
    """
    A tenant's self-serve request to move to a higher plan after paying by
    bank transfer. Mirrors the invoice payment-proof pattern: the tenant
    submits a reference/receipt, an admin reviews and approves or rejects.
    Approving actually changes Tenant.plan; rejecting just closes it out
    so the tenant can submit again if needed.
    """
    __tablename__ = "upgrade_requests"

    id              = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    requested_plan  = db.Column(db.String, nullable=False)  # "PRO" / "TEAM"
    note            = db.Column(db.Text, nullable=True)
    image_base64    = db.Column(db.Text, nullable=True)
    status          = db.Column(db.String, default="PENDING", nullable=False)  # PENDING / APPROVED / REJECTED
    created_at      = db.Column(db.DateTime, server_default=db.func.now())
    reviewed_at     = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "requested_plan": self.requested_plan,
            "note": self.note,
            "image_base64": self.image_base64,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
