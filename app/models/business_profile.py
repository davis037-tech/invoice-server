from uuid import uuid4
from sqlalchemy import ForeignKey
from ..extensions import db


class BusinessProfile(db.Model):
    """
    One of possibly several branded identities a tenant can invoice
    under — e.g. two different businesses run from the same Ledger
    account, each with its own name, logo, colors, and bank details.

    Settings (singular, one per tenant) remains the fallback/default
    identity for any tenant who never creates a profile, so nothing
    breaks for existing accounts. When an invoice references a
    BusinessProfile, that profile's branding is used instead of the
    tenant's default Settings.
    """
    __tablename__ = "business_profiles"

    id                 = db.Column(db.String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id          = db.Column(db.String, ForeignKey("tenants.id"), nullable=False)
    label              = db.Column(db.String, nullable=False)  # internal name, e.g. "Brand A" — not shown to clients
    business_name      = db.Column(db.String, nullable=True)
    business_logo      = db.Column(db.String, nullable=True)
    business_address   = db.Column(db.Text, nullable=True)
    primary_color      = db.Column(db.String, default="#C9A84C")
    bank_name          = db.Column(db.String, nullable=True)
    account_name       = db.Column(db.String, nullable=True)
    account_number     = db.Column(db.String, nullable=True)
    routing_number     = db.Column(db.String, nullable=True)
    swift_code         = db.Column(db.String, nullable=True)
    payment_notes      = db.Column(db.Text, nullable=True)
    is_default         = db.Column(db.Boolean, default=False, nullable=False)
    created_at         = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "label": self.label,
            "business_name": self.business_name,
            "business_logo": self.business_logo,
            "business_address": self.business_address,
            "primary_color": self.primary_color,
            "bank_name": self.bank_name,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "routing_number": self.routing_number,
            "swift_code": self.swift_code,
            "payment_notes": self.payment_notes,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def formatted_bank_details(self):
        lines = []
        if self.bank_name:
            lines.append(f"Bank: {self.bank_name}")
        if self.account_name:
            lines.append(f"Account name: {self.account_name}")
        if self.account_number:
            lines.append(f"Account number: {self.account_number}")
        if self.routing_number:
            lines.append(f"Routing/IBAN: {self.routing_number}")
        if self.swift_code:
            lines.append(f"SWIFT/BIC: {self.swift_code}")
        if self.payment_notes:
            lines.append(self.payment_notes)
        return "\n".join(lines) if lines else None
