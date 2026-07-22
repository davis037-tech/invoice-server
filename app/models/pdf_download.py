import uuid
from ..extensions import db


class PdfDownload(db.Model):
    """
    One row per PDF download. Counting rows in the last 7 days per tenant
    is how the weekly quota is enforced — same rolling-window approach
    used for invoice creation limits.
    """
    __tablename__ = "pdf_downloads"

    id          = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id   = db.Column(db.String, db.ForeignKey("tenants.id"), nullable=False)
    invoice_id  = db.Column(db.String, db.ForeignKey("invoices.id"), nullable=True)
    created_at  = db.Column(db.DateTime, server_default=db.func.now())
